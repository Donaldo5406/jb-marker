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
from ..deploy.ledger import load_ledger
from ..deploy.packager import package_channel
from ..deploy.providers import get_provider as get_deploy_provider
from ..deploy.rules_engine import load_policies
from ..observability import usage as usage_log
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


class DispatchBody(BaseModel):
    confirmed: bool = False


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
@router.post("/runs/{run_id}/deploy/setup")
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


@router.post("/runs/{run_id}/deploy/eligibility")
def deploy_eligibility(run_id: str, request: Request,
                       user_id: str = Depends(get_user_id)) -> dict:
    require_owner(request, run_id, user_id)
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


@router.post("/runs/{run_id}/deploy/packages")
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


@router.post("/runs/{run_id}/deploy/advisor/chat")
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


@router.post("/runs/{run_id}/deploy/dispatch")
def deploy_dispatch(run_id: str, body: DispatchBody, request: Request,
                    user_id: str = Depends(get_user_id)) -> dict:
    require_owner(request, run_id, user_id)
    if not body.confirmed:
        raise HTTPException(400, "user confirm required")
    if not entitlement.is_entitled(user_id):
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

    report = (
        f"# Deploy Report\n\n## Eligibility\n- Eligible: {len(recipients)}\n\n"
        f"## Channels\n{json.dumps(simulation, ensure_ascii=False, indent=2)}\n"
    )
    request.app.state.store.put_text(f"/{run_id}/deploy/report.md", report)
    request.app.state.store.set_step_status(run_id, "deploy", "PASS")
    return {"step_status": "PASS", "simulation": simulation}


@router.post("/runs/{run_id}/deploy/demo-payment")
def deploy_demo_payment(run_id: str, request: Request,
                        user_id: str = Depends(get_user_id)) -> dict:
    require_owner(request, run_id, user_id)
    entitlement.set_dev_pass(user_id)
    return {"dev_pass": True}


@router.get("/runs/{run_id}/deploy/_state")
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
