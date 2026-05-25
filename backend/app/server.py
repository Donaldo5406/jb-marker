"""FastAPI 앱 — 헬스 + runs + VFS CRUD + 게이트웨이 + WS _publish."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel

from .config import load_settings
from .gateway.gateway import MarkerGateway
from .gateway.harness import HarnessRequest, PassthroughHarness
from .providers.registry import get_provider
from .vfs.factory import get_vfs_store


class RunCreate(BaseModel):
    title: str | None = None
    languages: list[str] = []


class GatewayRun(BaseModel):
    run_id: str
    studio: str
    prompt: str
    provider: str = "fake"
    is_marker: bool = False


class PutText(BaseModel):
    content: str


class EntitlementPut(BaseModel):
    marker: bool


def _node_dict(n) -> dict[str, Any]:
    return {"path": n.path, "mime": n.mime, "source": n.source,
            "content_text": n.content_text, "meta": n.meta}


def create_app() -> FastAPI:
    app = FastAPI(title="JB Marker API")
    settings = load_settings()
    store = get_vfs_store(settings)

    # provider_factory: settings의 모델 매핑 주입
    model_map = {"anthropic": settings.anthropic_model, "openai": settings.openai_model,
                 "google": settings.google_model, "fake": "fake-1"}

    class _ModelBoundProvider:
        def __init__(self, name: str):
            self._p = get_provider(name, settings)
            self._model = model_map.get(name, "fake-1")

        def complete(self, messages, *, model=None, system=None, **kw):
            return self._p.complete(messages, model=self._model, system=system, **kw)

    entitlement_state = {"marker": settings.entitlement_override}
    gateway = MarkerGateway(store,
                            entitlement_override=lambda: entitlement_state["marker"],
                            provider_factory=_ModelBoundProvider)

    connections: dict[str, set[WebSocket]] = {}

    async def _publish(run_id: str, event: dict) -> None:
        for ws in list(connections.get(run_id, set())):
            try:
                await ws.send_json(event)
            except Exception:
                connections.get(run_id, set()).discard(ws)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/entitlement")
    def get_entitlement() -> dict:
        return {"marker": entitlement_state["marker"]}

    @app.put("/entitlement")
    def put_entitlement(body: EntitlementPut) -> dict:
        entitlement_state["marker"] = body.marker
        return {"marker": entitlement_state["marker"]}

    @app.post("/runs")
    def create_run(body: RunCreate) -> dict:
        run_id = uuid.uuid4().hex[:12]
        m = store.create_run(run_id, title=body.title, languages=body.languages)
        return {"run_id": m.run_id, "title": m.title}

    @app.get("/runs")
    def list_runs(user_id: str = "demo") -> dict:
        runs = store.list_runs(user_id=user_id)
        return {"runs": [{"run_id": m.run_id, "title": m.title,
                          "created_at": m.created_at,
                          "step_status": m.step_status} for m in runs]}

    @app.post("/gateway/run")
    async def gateway_run(body: GatewayRun) -> dict:
        if store.get_manifest(body.run_id) is None:
            raise HTTPException(404, "run 없음")
        req = HarnessRequest(run_id=body.run_id, studio=body.studio,
                             user_prompt=body.prompt, provider=body.provider,
                             is_marker=body.is_marker)
        try:
            result = gateway.run(req, PassthroughHarness())
        except PermissionError as e:
            raise HTTPException(402, str(e))
        await _publish(body.run_id, {"type": "artifact", "path": result.output_path})
        return {"output_path": result.output_path, "text": result.text}

    @app.get("/vfs/{run_id}")
    def vfs_list(run_id: str, prefix: str | None = None) -> dict:
        nodes = store.list(prefix or f"/{run_id}")
        return {"nodes": [_node_dict(n) for n in nodes]}

    @app.get("/vfs/{run_id}/{rest:path}")
    def vfs_get(run_id: str, rest: str):
        node = store.get(f"/{run_id}/{rest}")
        if node is None:
            raise HTTPException(404, "노드 없음")
        if node.blob is not None or node.blob_path is not None:
            loaded = store.get(node.path)
            return Response(content=loaded.blob or b"", media_type=node.mime or "application/octet-stream")
        return _node_dict(node)

    @app.put("/vfs/{run_id}/{rest:path}")
    def vfs_put(run_id: str, rest: str, body: PutText) -> dict:
        node = store.put(f"/{run_id}/{rest}", body.content, source="user", mime="text/markdown")
        return _node_dict(node)

    @app.websocket("/ws/{run_id}")
    async def ws(websocket: WebSocket, run_id: str):
        await websocket.accept()
        connections.setdefault(run_id, set()).add(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            connections.get(run_id, set()).discard(websocket)

    return app


app = create_app()
