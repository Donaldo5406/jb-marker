"""FastAPI 앱 — 헬스 + runs + VFS CRUD + 게이트웨이 + WS _publish."""
from __future__ import annotations

import json
import time
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from . import entitlement
from .auth import make_user_id_dep
from .config import load_settings
from .deploy.adapters.base import Package, ScheduleSpec
from .deploy.adapters.registry import get_adapter
from .deploy.advisor.chat import DeployAdvisor
from .deploy.advisor.scripted import ScriptedAdvisorProvider
from .deploy.eligibility import build_eligibility
from .deploy.ledger import load_ledger
from .deploy.packager import package_channel
from .deploy.providers import get_provider as get_deploy_provider
from .deploy.rules_engine import load_policies
from .gateway.gateway import MarkerGateway
from .gateway.harness import HarnessRequest
from .gateway.registry import select_harness
from .history.gallery import build_gallery
from .history.preview import build_preview_html
from .observability import usage as usage_log
from .providers.wrappers import ModelBoundProvider, TrackedProvider
from .routers import meta as meta_router
from .routers import runs as runs_router
from .routers.deps import require_owner_factory as _require_run_owner_factory
from .session.liveness import Thresholds
from .session.store import SessionStore
from .vfs.factory import get_vfs_store


class GatewayRun(BaseModel):
    run_id: str
    studio: str
    prompt: str
    provider: str = "fake"
    is_marker: bool = False
    answer: str | None = None
    action: str | None = None
    bypass_map: dict | None = None
    mock: bool = False   # 시연용 전역 Mock — true면 전 provider를 fake로 강제(요청 단위)


class PutText(BaseModel):
    content: str
    mime: str | None = None
    # "base64" → 백엔드가 디코드해 bytes로 저장 (PNG 등 바이너리 라운드트립용)
    content_encoding: str | None = None


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


def _node_dict(n) -> dict[str, Any]:
    return {"path": n.path, "mime": n.mime, "source": n.source,
            "content_text": n.content_text, "meta": n.meta}


def create_app() -> FastAPI:
    app = FastAPI(title="JB Marker API")
    settings = load_settings()
    # 분리형 배포: env로 명시한 origin(예: https://*.vercel.app) 화이트리스트 +
    # localhost regex 폴백. allow_credentials=True라 wildcard("*") 불가 → 명시 리스트.
    _dev_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    _origins = list(settings.cors_allow_origins) or _dev_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    store = get_vfs_store(settings)

    session_store = SessionStore(store, Thresholds(
        stall_ms=settings.session_stall_ms,
        suspend_ms=settings.session_suspend_ms,
        retention_ms=settings.session_retention_ms,
    ))

    # 라우터 공유 상태 — 모듈 싱글턴 금지, 전부 app.state 경유 (spec §8.1)
    app.state.settings = settings
    app.state.store = store
    app.state.session_store = session_store

    app.include_router(meta_router.router)
    app.include_router(runs_router.router)

    def _now_ms() -> int:
        return int(time.time() * 1000)

    user_id_dep = make_user_id_dep(settings)
    require_owner = _require_run_owner_factory(store)

    from .entitlement import set_store
    from .entitlement_store import get_entitlement_store
    set_store(get_entitlement_store(settings))
    entitlement.set_override_source(lambda: settings.entitlement_override)

    # provider_factory: settings의 모델 매핑 주입
    def _provider_factory(name: str):
        return ModelBoundProvider(name, settings)

    def _wrap_for_usage(provider, req):
        return TrackedProvider(provider, store=store, run_id=req.run_id,
                               step=req.studio or "gateway", settings=settings)

    gateway = MarkerGateway(store,
                            entitlement_check=entitlement.is_entitled,
                            provider_factory=_provider_factory,
                            wrap_provider=_wrap_for_usage)

    connections: dict[str, set[WebSocket]] = {}

    async def _publish(run_id: str, event: dict) -> None:
        for ws in list(connections.get(run_id, set())):
            try:
                await ws.send_json(event)
            except Exception:
                connections.get(run_id, set()).discard(ws)

    @app.post("/gateway/run")
    async def gateway_run(body: GatewayRun, user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(body.run_id, user_id)
        provider_name = "demo" if body.mock else body.provider
        req = HarnessRequest(run_id=body.run_id, studio=body.studio,
                             user_prompt=body.prompt, provider=provider_name,
                             is_marker=body.is_marker, answer=body.answer,
                             action=body.action, user_id=user_id,
                             bypass_map=body.bypass_map)
        media_name = "demo" if body.mock else "google"

        def _media_provider():
            # 주입형 image/vision provider도 usage 추적 래핑 (spec §7-2).
            return TrackedProvider(ModelBoundProvider(media_name, settings),
                                   store=store, run_id=body.run_id,
                                   step=body.studio, settings=settings)

        harness = select_harness(body.studio, body.is_marker,
                                 media_provider_factory=_media_provider)
        try:
            result = gateway.run(req, harness)
        except PermissionError as e:
            raise HTTPException(402, str(e))
        now = _now_ms()
        kind = "ask_answer" if body.answer is not None else "user_turn"
        hb = session_store.heartbeat(body.run_id, body.studio, now)
        reactivated = bool(hb.get("exists")) and hb.get("status") != "active"
        session_store.touch(body.run_id, body.studio, now, kind=kind)
        if reactivated:
            result.meta["session_event"] = "restored"
            await _publish(body.run_id, {"type": "session", "event": "restored",
                                         "studio": body.studio, "run_id": body.run_id})
        for ev in result.events:
            await _publish(body.run_id, ev)
        return {"output_path": result.output_path, "text": result.text,
                "gate": result.gate.to_dict() if result.gate else None,
                "meta": result.meta}

    @app.get("/runs/{run_id}/session/{studio}")
    def session_heartbeat(run_id: str, studio: str,
                          user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
        return session_store.heartbeat(run_id, studio, _now_ms())

    @app.post("/runs/{run_id}/session/{studio}/resume")
    def session_resume(run_id: str, studio: str,
                       user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
        return session_store.resume(run_id, studio, _now_ms())

    @app.post("/runs/{run_id}/session/{studio}/suspend")
    def session_suspend(run_id: str, studio: str,
                        user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
        return session_store.suspend(run_id, studio, _now_ms())

    @app.get("/runs/{run_id}/sessions")
    def session_list(run_id: str,
                     user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
        return session_store.list(run_id, _now_ms())

    @app.get("/vfs/{run_id}")
    def vfs_list(run_id: str, prefix: str | None = None,
                 user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
        nodes = store.list(prefix or f"/{run_id}")
        return {"nodes": [_node_dict(n) for n in nodes]}

    @app.get("/vfs/{run_id}/{rest:path}")
    def vfs_get(run_id: str, rest: str, user_id: str = Depends(user_id_dep)):
        require_owner(run_id, user_id)
        node = store.get(f"/{run_id}/{rest}")
        if node is None:
            raise HTTPException(404, "노드 없음")
        if node.blob is not None or node.blob_path is not None:
            # node.blob 은 store.get()이 이미 로드함(Local·Supabase 공통) — 재조회 불필요.
            return Response(content=node.blob or b"", media_type=node.mime or "application/octet-stream")
        return _node_dict(node)

    @app.put("/vfs/{run_id}/{rest:path}")
    def vfs_put(run_id: str, rest: str, body: PutText,
                user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
        mime = body.mime or ("application/json" if rest.endswith(".json") else "text/markdown")
        # base64 인코딩 본문이면 bytes로 디코드해 저장 (PNG 등 바이너리 라운드트립).
        # 미지정 시 기존 텍스트 경로 유지(하위호환).
        if body.content_encoding == "base64":
            import base64
            try:
                raw = base64.b64decode(body.content, validate=True)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"base64 decode failed: {e}")
            node = store.put(f"/{run_id}/{rest}", raw, source="frontend", mime=mime)
        else:
            node = store.put(f"/{run_id}/{rest}", body.content, source="user", mime=mime)
        return _node_dict(node)

    # === M6 DeployStudio routes ===
    @app.post("/runs/{run_id}/deploy/setup")
    def deploy_setup(run_id: str, body: DeploySetupBody,
                     user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
        matrix = [{"channel": p, "lang": l}
                  for p in body.selected_providers for l in body.languages]
        store.put_text(
            f"/{run_id}/deploy/inputs/selected_providers.json",
            json.dumps(body.selected_providers, ensure_ascii=False),
        )
        store.put_text(
            f"/{run_id}/deploy/inputs/matrix.json",
            json.dumps(matrix, ensure_ascii=False),
        )
        store.set_step_status(run_id, "deploy", "in_progress")
        return {"matrix": matrix, "step_status": "in_progress"}

    @app.post("/runs/{run_id}/deploy/eligibility")
    def deploy_eligibility(run_id: str, user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
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
        store.put_text(
            f"/{run_id}/deploy/eligibility/recipients.json",
            json.dumps(result["recipients"], ensure_ascii=False),
        )
        store.put_text(
            f"/{run_id}/deploy/eligibility/excluded.json",
            json.dumps(sanitized_excluded, ensure_ascii=False),
        )
        store.put_text(
            f"/{run_id}/deploy/eligibility/calendar.json",
            json.dumps(result["calendar"], ensure_ascii=False),
        )
        return {
            "total": result["total"],
            "eligible_count": result["eligible_count"],
            "excluded_count": len(result["excluded"]),
            "breakdown": result["breakdown"],   # 정책별(§50/§15·§16) 사유 분해
        }

    @app.post("/runs/{run_id}/deploy/packages")
    def deploy_packages(run_id: str, body: DeployPackageBody,
                        user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
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
            store.put_text(
                f"/{run_id}/deploy/packages/{package_id}/copy.md",
                pkg["copy_text"],
            )
        store.put_text(
            f"/{run_id}/deploy/packages/{package_id}/copy.meta.json",
            json.dumps(pkg, ensure_ascii=False),
        )
        store.put_text(
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

    def _make_advisor_provider(ctx: dict, channel: str, mock: bool = False):
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
            from .deploy.advisor.live import AnthropicAdvisorProvider
            return AnthropicAdvisorProvider(
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_advisor_model,
                ctx=ctx,
                channel=channel,
            )
        return ScriptedAdvisorProvider(ctx=ctx, channel=channel)

    @app.post("/runs/{run_id}/deploy/advisor/chat")
    def deploy_advisor_chat(run_id: str, body: AdvisorChatBody,
                            user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
        if not entitlement.is_entitled(user_id):
            raise HTTPException(402, "Payment required (entitlement)")
        ctx_raw = store.get_text(f"/{run_id}/deploy/packages/{body.package_id}/copy.meta.json")
        ctx = json.loads(ctx_raw) if ctx_raw else {}
        channel = body.package_id.split("_", 1)[0] if "_" in body.package_id else "sms"
        provider = _make_advisor_provider(ctx, channel, mock=body.mock)
        h = DeployAdvisor(provider=provider, vfs_store=store, run_id=run_id)
        result = h.handle_turn(package_id=body.package_id, user_message=body.message)
        # advisor live LLM이 usage 노출 시 영속(scripted는 _usage 없음 → skip).
        if "_usage" in result:
            usage_log.record_usage(
                store, run_id=run_id, step="advisor",
                model=result.get("_model") or settings.anthropic_advisor_model,
                kind="text", usage=result["_usage"],
                meta={"package_id": body.package_id},
            )
        # 내부 키는 영속(record_usage) 후 HTTP 응답에서 제거 — 명세 표면 위생 (spec §8.2).
        result.pop("_usage", None)
        result.pop("_model", None)
        return result

    @app.get("/runs/{run_id}/usage")
    def get_usage(run_id: str, user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
        return usage_log.summarize(store, run_id=run_id)

    @app.get("/runs/{run_id}/gallery")
    def get_gallery(run_id: str, user_id: str = Depends(user_id_dep)) -> dict:
        man = require_owner(run_id, user_id)
        nodes = store.list(f"/{run_id}")
        return build_gallery(man, nodes)

    @app.get("/runs/{run_id}/preview")
    def get_preview(run_id: str, user_id: str = Depends(user_id_dep)):
        require_owner(run_id, user_id)
        markup = build_preview_html(run_id, store)
        return Response(content=markup, media_type="text/html")

    @app.post("/runs/{run_id}/deploy/dispatch")
    def deploy_dispatch(run_id: str, body: DispatchBody,
                        user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
        if not body.confirmed:
            raise HTTPException(400, "user confirm required")
        if not entitlement.is_entitled(user_id):
            raise HTTPException(402, "Payment required (entitlement)")

        selected = json.loads(
            store.get_text(f"/{run_id}/deploy/inputs/selected_providers.json") or "[]"
        )
        recipients = json.loads(
            store.get_text(f"/{run_id}/deploy/eligibility/recipients.json") or "[]"
        )
        if len(recipients) == 0:
            raise HTTPException(400, "no eligible recipients")
        if len(selected) == 0:
            raise HTTPException(400, "no provider selected")

        matrix = json.loads(store.get_text(f"/{run_id}/deploy/inputs/matrix.json") or "[]")
        plan = {"send_hour": 10, "channels": selected, "recipients_count": len(recipients)}
        simulation: list[dict] = []
        for cell in matrix:
            adapter = get_adapter(cell["channel"])
            copy_meta_raw = store.get_text(
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

        store.put_text(
            f"/{run_id}/deploy/dispatch/plan.json",
            json.dumps(plan, ensure_ascii=False),
        )
        store.put_text(
            f"/{run_id}/deploy/dispatch/simulation.json",
            json.dumps(simulation, ensure_ascii=False),
        )

        report = (
            f"# Deploy Report\n\n## Eligibility\n- Eligible: {len(recipients)}\n\n"
            f"## Channels\n{json.dumps(simulation, ensure_ascii=False, indent=2)}\n"
        )
        store.put_text(f"/{run_id}/deploy/report.md", report)
        store.set_step_status(run_id, "deploy", "PASS")
        return {"step_status": "PASS", "simulation": simulation}

    @app.post("/runs/{run_id}/deploy/demo-payment")
    def deploy_demo_payment(run_id: str, user_id: str = Depends(user_id_dep)) -> dict:
        require_owner(run_id, user_id)
        entitlement.set_dev_pass(user_id)
        return {"dev_pass": True}

    @app.get("/runs/{run_id}/deploy/_state")
    def deploy_state(run_id: str, user_id: str = Depends(user_id_dep)) -> dict:
        m = require_owner(run_id, user_id)
        return {
            "step_status": m.step_status.get("deploy", "idle"),
            "selected_providers": json.loads(
                store.get_text(f"/{run_id}/deploy/inputs/selected_providers.json") or "[]"
            ),
            "matrix": json.loads(
                store.get_text(f"/{run_id}/deploy/inputs/matrix.json") or "[]"
            ),
            "dev_pass": entitlement.is_entitled(user_id),
        }

    @app.websocket("/ws/{run_id}")
    async def ws(websocket: WebSocket, run_id: str):
        token = websocket.query_params.get("token")
        from .auth import resolve_user_id, AuthError
        try:
            uid = resolve_user_id(f"Bearer {token}" if token else None, settings)
            m = store.get_manifest(run_id)
            if m is None or m.user_id != uid:
                await websocket.close(code=4404)
                return
        except AuthError:
            await websocket.close(code=4401)
            return
        await websocket.accept()
        connections.setdefault(run_id, set()).add(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            connections.get(run_id, set()).discard(websocket)

    return app


app = create_app()
