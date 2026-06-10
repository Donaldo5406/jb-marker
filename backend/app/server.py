"""FastAPI 앱 팩토리 — 게이트웨이+WS는 잔존, 나머지 라우트는 routers/ (P4 분해 중)."""
from __future__ import annotations

import time

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import entitlement
from .auth import make_user_id_dep
from .config import load_settings
from .gateway.gateway import MarkerGateway
from .gateway.harness import HarnessRequest
from .gateway.registry import select_harness
from .providers.wrappers import ModelBoundProvider, TrackedProvider
from .routers import deploy as deploy_router
from .routers import history as history_router
from .routers import meta as meta_router
from .routers import observability as observability_router
from .routers import runs as runs_router
from .routers import session as session_router
from .routers import vfs as vfs_router
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
    app.include_router(session_router.router)
    app.include_router(vfs_router.router)
    app.include_router(observability_router.router)
    app.include_router(history_router.router)
    app.include_router(deploy_router.router)

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
