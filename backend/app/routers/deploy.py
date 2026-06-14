"""[deploy] M6 DeployStudio — setup·eligibility·packages·advisor·dispatch·demo-payment·_state (spec §8.1)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .. import entitlement
from ..deploy.adapters.base import Package, ScheduleSpec
from ..deploy.adapters.registry import get_adapter
from ..deploy.advisor.chat import DeployAdvisor
from ..deploy.advisor.scripted import ScriptedAdvisorProvider
from ..deploy.eligibility import build_eligibility
from ..deploy.ledger import load_ledger, normalize_recipients
from ..deploy.packager import package_channel
from ..deploy.providers import get_provider as get_deploy_provider
from ..deploy.rules_engine import load_policies
from ..observability import usage as usage_log
from ..schemas import (
    OWNER_RESPONSES,
    AdvisorErrorOut,
    AdvisorOkOut,
    DemoPaymentOut,
    DeploySetupOut,
    DeployStateOut,
    DispatchOut,
    EligibilityOut,
    ErrorOut,
    PackageOut,
)
from .deps import get_user_id, require_owner

router = APIRouter(tags=["deploy"])


# === M6 DeployStudio request bodies ===
class DeploySetupBody(BaseModel):
    selected_providers: list[str]
    languages: list[str]


class DeployPackageBody(BaseModel):
    channel: str
    lang: str
    original_copy: str
    visual_path: str


class AdvisorChatBody(BaseModel):
    package_id: str
    message: str
    mock: bool = False   # 시연용 — true면 advisor를 scripted(LLM 없음)로 강제


class DeployEligibilityBody(BaseModel):
    # 업로드 발송 명단(없으면 내장 consent_ledger fixture 사용). CSV→JSON 행 배열.
    recipients: list[dict] | None = None


class DispatchBody(BaseModel):
    confirmed: bool = False
    mock: bool = False   # 시연용 — true면 Pro+ 결제(entitlement) 게이트를 우회해 리포트까지 산출


def _make_advisor_provider(ctx: dict, channel: str, settings, mock: bool = False):
    """advisor_mode 분기 — mock: 강제 scripted, auto: 키 있으면 live, scripted: 강제 scripted, live: 키 필수.

    실LLM 배선 실패(SDK import / 호출 예외)는 호출부에서 잡아 422로 변환.
    """
    if mock:
        return ScriptedAdvisorProvider(ctx=ctx, channel=channel)
    mode = settings.advisor_mode
    has_key = bool(settings.anthropic_api_key)
    if mode == "live" or (mode == "auto" and has_key):
        if not has_key:
            raise HTTPException(422, "ADVISOR_MODE=live but ANTHROPIC_API_KEY is empty")
        from ..deploy.advisor.live import AnthropicAdvisorProvider
        return AnthropicAdvisorProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_advisor_model,
            ctx=ctx,
            channel=channel,
        )
    return ScriptedAdvisorProvider(ctx=ctx, channel=channel)


# === M6 DeployStudio routes ===
@router.post("/runs/{run_id}/deploy/setup", response_model=DeploySetupOut,
             summary="배포 매트릭스(채널×언어) 설정",
             responses=OWNER_RESPONSES)
def deploy_setup(run_id: str, body: DeploySetupBody, request: Request,
                 user_id: str = Depends(get_user_id)) -> dict:
    require_owner(request, run_id, user_id)
    matrix = [{"channel": p, "lang": l}
              for p in body.selected_providers for l in body.languages]
    request.app.state.store.put_text(
        f"/{run_id}/deploy/inputs/selected_providers.json",
        json.dumps(body.selected_providers, ensure_ascii=False),
    )
    request.app.state.store.put_text(
        f"/{run_id}/deploy/inputs/matrix.json",
        json.dumps(matrix, ensure_ascii=False),
    )
    request.app.state.store.set_step_status(run_id, "deploy", "in_progress")
    return {"matrix": matrix, "step_status": "in_progress"}


@router.post("/runs/{run_id}/deploy/eligibility", response_model=EligibilityOut,
             summary="수신자 적격성(D1) 산출 — 정책 룰 엔진",
             responses=OWNER_RESPONSES)
def deploy_eligibility(run_id: str, request: Request,
                       body: DeployEligibilityBody | None = None,
                       user_id: str = Depends(get_user_id)) -> dict:
    require_owner(request, run_id, user_id)
    # 업로드 명단이 있으면 그것을, 없으면 내장 fixture(consent_ledger)를 ledger로 사용.
    uploaded = normalize_recipients(body.recipients) if (body and body.recipients) else []
    if uploaded:
        ledger = uploaded
        request.app.state.store.put_text(
            f"/{run_id}/deploy/inputs/recipients_uploaded.json",
            json.dumps(uploaded, ensure_ascii=False),
        )
    else:
        ledger = load_ledger()
    policies = load_policies()
    result = build_eligibility(ledger, policies, send_hour=10)
    # rules_engine.evaluate_recipient: primary["all_blocks"] = blocks
    # where blocks contains primary → 자기참조. 직렬화 전 단일 단계만 펼친다.
    sanitized_excluded = []
    for ex in result["excluded"]:
        flat_blocks = [
            {k: v for k, v in b.items() if k != "all_blocks"}
            for b in ex.get("all_blocks", [])
        ]
        sanitized_excluded.append({
            **{k: v for k, v in ex.items() if k != "all_blocks"},
            "all_blocks": flat_blocks,
        })
    request.app.state.store.put_text(
        f"/{run_id}/deploy/eligibility/recipients.json",
        json.dumps(result["recipients"], ensure_ascii=False),
    )
    request.app.state.store.put_text(
        f"/{run_id}/deploy/eligibility/excluded.json",
        json.dumps(sanitized_excluded, ensure_ascii=False),
    )
    request.app.state.store.put_text(
        f"/{run_id}/deploy/eligibility/calendar.json",
        json.dumps(result["calendar"], ensure_ascii=False),
    )
    return {
        "total": result["total"],
        "eligible_count": result["eligible_count"],
        "excluded_count": len(result["excluded"]),
        "breakdown": result["breakdown"],   # 정책별(§50/§15·§16) 사유 분해
    }


@router.post("/runs/{run_id}/deploy/packages", response_model=PackageOut,
             summary="채널×언어 패키지(카피 적응) 생성",
             responses=OWNER_RESPONSES)
def deploy_packages(run_id: str, body: DeployPackageBody, request: Request,
                    user_id: str = Depends(get_user_id)) -> dict:
    require_owner(request, run_id, user_id)
    provider = get_deploy_provider(body.channel)
    pkg = package_channel(
        channel=body.channel,
        lang=body.lang,
        original_copy=body.original_copy,
        provider=provider,
        visual_path=body.visual_path,
    )
    package_id = f"{body.channel}_{body.lang}"
    if pkg["status"] == "ok":
        request.app.state.store.put_text(
            f"/{run_id}/deploy/packages/{package_id}/copy.md",
            pkg["copy_text"],
        )
    request.app.state.store.put_text(
        f"/{run_id}/deploy/packages/{package_id}/copy.meta.json",
        json.dumps(pkg, ensure_ascii=False),
    )
    request.app.state.store.put_text(
        f"/{run_id}/deploy/packages/{package_id}/package.meta.json",
        json.dumps(
            {
                "channel": body.channel,
                "lang": body.lang,
                "spec_id": provider.id,
                "adapter_status": provider.adapter_status,
            },
            ensure_ascii=False,
        ),
    )
    return {"package_id": package_id, "status": pkg["status"], "reason": pkg.get("reason")}


@router.post("/runs/{run_id}/deploy/advisor/chat",
             response_model=AdvisorOkOut | AdvisorErrorOut,
             summary="D2 어드바이저 멀티턴 챗(도구 화이트리스트·grounding 검증)",
             responses={**OWNER_RESPONSES, 402: {"model": ErrorOut},
                        422: {"model": ErrorOut}})
def deploy_advisor_chat(run_id: str, body: AdvisorChatBody, request: Request,
                        user_id: str = Depends(get_user_id)) -> dict:
    require_owner(request, run_id, user_id)
    if not entitlement.is_entitled(user_id):
        raise HTTPException(402, "Payment required (entitlement)")
    ctx_raw = request.app.state.store.get_text(f"/{run_id}/deploy/packages/{body.package_id}/copy.meta.json")
    ctx = json.loads(ctx_raw) if ctx_raw else {}
    channel = body.package_id.split("_", 1)[0] if "_" in body.package_id else "sms"
    provider = _make_advisor_provider(ctx, channel, request.app.state.settings, mock=body.mock)
    h = DeployAdvisor(provider=provider, vfs_store=request.app.state.store, run_id=run_id)
    result = h.handle_turn(package_id=body.package_id, user_message=body.message)
    # advisor live LLM이 usage 노출 시 영속(scripted는 _usage 없음 → skip).
    if "_usage" in result:
        usage_log.record_usage(
            request.app.state.store, run_id=run_id, step="advisor",
            model=result.get("_model") or request.app.state.settings.anthropic_advisor_model,
            kind="text", usage=result["_usage"],
            meta={"package_id": body.package_id},
        )
    # 내부 키는 영속(record_usage) 후 HTTP 응답에서 제거 — 명세 표면 위생 (spec §8.2).
    result.pop("_usage", None)
    result.pop("_model", None)
    return result


@router.post("/runs/{run_id}/deploy/dispatch", response_model=DispatchOut,
             summary="발송 시뮬레이션 디스패치(확인 필수)",
             responses={**OWNER_RESPONSES, 400: {"model": ErrorOut},
                        402: {"model": ErrorOut}})
def deploy_dispatch(run_id: str, body: DispatchBody, request: Request,
                    user_id: str = Depends(get_user_id)) -> dict:
    m = require_owner(request, run_id, user_id)
    if not body.confirmed:
        raise HTTPException(400, "user confirm required")
    # mock(시연)은 Pro+ 결제 게이트를 우회 — 데모에서 결제 단계 없이도 리포트까지 산출.
    # 실사용(mock=false)은 기존대로 entitlement 필수(402).
    if not body.mock and not entitlement.is_entitled(user_id):
        raise HTTPException(402, "Payment required (entitlement)")

    selected = json.loads(
        request.app.state.store.get_text(f"/{run_id}/deploy/inputs/selected_providers.json") or "[]"
    )
    recipients = json.loads(
        request.app.state.store.get_text(f"/{run_id}/deploy/eligibility/recipients.json") or "[]"
    )
    if len(recipients) == 0:
        raise HTTPException(400, "no eligible recipients")
    if len(selected) == 0:
        raise HTTPException(400, "no provider selected")

    matrix = json.loads(request.app.state.store.get_text(f"/{run_id}/deploy/inputs/matrix.json") or "[]")
    plan = {"send_hour": 10, "channels": selected, "recipients_count": len(recipients)}
    simulation: list[dict] = []
    for cell in matrix:
        adapter = get_adapter(cell["channel"])
        copy_meta_raw = request.app.state.store.get_text(
            f"/{run_id}/deploy/packages/{cell['channel']}_{cell['lang']}/copy.meta.json"
        )
        if not copy_meta_raw:
            continue
        meta = json.loads(copy_meta_raw)
        if meta.get("status") == "needs_advisor" and meta.get("grounding_check") != "ok":
            simulation.append({
                "channel": cell["channel"], "lang": cell["lang"],
                "status": "skipped",
                "reason": "grounding_fail or needs_advisor",
            })
            continue
        pkg = Package(
            channel=cell["channel"],
            lang=cell["lang"],
            visual_path=meta.get("visual_path", ""),
            copy_text=meta.get("copy_text", meta.get("adapted_text", "")),
            meta=meta,
        )
        recs_for_lang = [r for r in recipients if r["lang"] == cell["lang"]]
        res = adapter.dispatch(cell["channel"], pkg, ScheduleSpec(send_hour=10), recs_for_lang)
        simulation.append({
            "channel": cell["channel"], "lang": cell["lang"],
            "status": res.status, "message": res.message,
            "recipients_count": res.recipients_count,
        })

    request.app.state.store.put_text(
        f"/{run_id}/deploy/dispatch/plan.json",
        json.dumps(plan, ensure_ascii=False),
    )
    request.app.state.store.put_text(
        f"/{run_id}/deploy/dispatch/simulation.json",
        json.dumps(simulation, ensure_ascii=False),
    )

    # 리치 리포트 — 적법성 요약(정책별 제외)·채널별 결과·컴플라이언스 근거.
    excluded = json.loads(
        request.app.state.store.get_text(f"/{run_id}/deploy/eligibility/excluded.json") or "[]"
    )
    total = len(recipients) + len(excluded)
    _policy_label = {
        "infomatics": "정보통신망법 §50 (미동의·야간·수신거부)",
        "pipa": "개인정보보호법 §15·§16 (수집목적·보유기간)",
    }
    by_policy: dict[str, int] = {}
    for ex in excluded:
        pol = _policy_label.get(ex.get("policy"), ex.get("policy") or "기타")
        by_policy[pol] = by_policy.get(pol, 0) + 1
    sent_cells = [s for s in simulation if s.get("status") != "skipped"]
    skipped_cells = [s for s in simulation if s.get("status") == "skipped"]
    sent_recipients = sum(s.get("recipients_count", 0) for s in sent_cells)
    title = getattr(m, "title", None) or run_id

    rows = "\n".join(
        f"| {s['channel']} | {s['lang']} | "
        f"{'건너뜀' if s.get('status') == 'skipped' else '발송(시뮬)'} | "
        f"{s.get('recipients_count', 0)} | {s.get('reason') or s.get('message') or '-'} |"
        for s in simulation
    ) or "| - | - | - | 0 | 발송 대상 없음 |"
    pol_lines = "\n".join(f"- {pol}: {n}건" for pol, n in by_policy.items()) or "- 제외 없음"

    report = f"""# 발송 리포트 (Deploy Report)

- **캠페인**: {title}
- **발송 채널**: {", ".join(selected) or "-"}
- **발송 방식**: 시뮬레이션(STUB) — 실 연동 시 실제 발송

## 1. 발송 적법성 요약
- 전체 수신자: **{total}명**
- 발송 대상(적격): **{len(recipients)}명**
- 제외: **{len(excluded)}명**

### 제외 사유 (정책별)
{pol_lines}

## 2. 채널별 발송 결과
| 채널 | 언어 | 상태 | 발송 수 | 비고 |
|------|------|------|--------:|------|
{rows}

- 발송(시뮬) 채널 {len(sent_cells)}개 · 건너뜀 {len(skipped_cells)}개
- 누적 발송 수(시뮬): **{sent_recipients}명**

## 3. 컴플라이언스 근거
- **정보통신망법 §50**: 야간(21~08시) 발송 차단, 수신거부(opt-out)·미동의 수신자 제외.
- **개인정보보호법 §15·§16**: 수집목적 합치·보유기간 이내 수신자만 발송.
- 본 발송은 사용자 확정 게이트를 통과한 **시뮬레이션**입니다 — 규칙엔진은 자동 발송하지 않습니다.
"""
    request.app.state.store.put_text(f"/{run_id}/deploy/report.md", report)
    request.app.state.store.set_step_status(run_id, "deploy", "PASS")
    return {"step_status": "PASS", "simulation": simulation}


@router.post("/runs/{run_id}/deploy/demo-payment", response_model=DemoPaymentOut,
             summary="데모 결제 — dev_pass 부여",
             responses=OWNER_RESPONSES)
def deploy_demo_payment(run_id: str, request: Request,
                        user_id: str = Depends(get_user_id)) -> dict:
    require_owner(request, run_id, user_id)
    entitlement.set_dev_pass(user_id)
    return {"dev_pass": True}


@router.get("/runs/{run_id}/deploy/_state", response_model=DeployStateOut,
            summary="배포 스튜디오 상태 스냅샷",
            responses=OWNER_RESPONSES)
def deploy_state(run_id: str, request: Request,
                 user_id: str = Depends(get_user_id)) -> dict:
    m = require_owner(request, run_id, user_id)
    return {
        "step_status": m.step_status.get("deploy", "idle"),
        "selected_providers": json.loads(
            request.app.state.store.get_text(f"/{run_id}/deploy/inputs/selected_providers.json") or "[]"
        ),
        "matrix": json.loads(
            request.app.state.store.get_text(f"/{run_id}/deploy/inputs/matrix.json") or "[]"
        ),
        "dev_pass": entitlement.is_entitled(user_id),
    }
