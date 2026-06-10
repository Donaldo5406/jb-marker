"""[vfs] VFS 노드 list/get/put (spec §8.1)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from .deps import get_user_id, require_owner

router = APIRouter(tags=["vfs"])


class PutText(BaseModel):
    content: str
    mime: str | None = None
    # "base64" → 백엔드가 디코드해 bytes로 저장 (PNG 등 바이너리 라운드트립용)
    content_encoding: str | None = None


def _node_dict(n) -> dict[str, Any]:
    return {"path": n.path, "mime": n.mime, "source": n.source,
            "content_text": n.content_text, "meta": n.meta}


@router.get("/vfs/{run_id}")
def vfs_list(run_id: str, request: Request, prefix: str | None = None,
             user_id: str = Depends(get_user_id)) -> dict:
    require_owner(request, run_id, user_id)
    nodes = request.app.state.store.list(prefix or f"/{run_id}")
    return {"nodes": [_node_dict(n) for n in nodes]}


@router.get("/vfs/{run_id}/{rest:path}")
def vfs_get(run_id: str, rest: str, request: Request,
            user_id: str = Depends(get_user_id)):
    require_owner(request, run_id, user_id)
    node = request.app.state.store.get(f"/{run_id}/{rest}")
    if node is None:
        raise HTTPException(404, "노드 없음")
    if node.blob is not None or node.blob_path is not None:
        # node.blob 은 store.get()이 이미 로드함(Local·Supabase 공통) — 재조회 불필요.
        return Response(content=node.blob or b"", media_type=node.mime or "application/octet-stream")
    return _node_dict(node)


@router.put("/vfs/{run_id}/{rest:path}")
def vfs_put(run_id: str, rest: str, body: PutText, request: Request,
            user_id: str = Depends(get_user_id)) -> dict:
    require_owner(request, run_id, user_id)
    mime = body.mime or ("application/json" if rest.endswith(".json") else "text/markdown")
    # base64 인코딩 본문이면 bytes로 디코드해 저장 (PNG 등 바이너리 라운드트립).
    # 미지정 시 기존 텍스트 경로 유지(하위호환).
    if body.content_encoding == "base64":
        import base64
        try:
            raw = base64.b64decode(body.content, validate=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"base64 decode failed: {e}")
        node = request.app.state.store.put(f"/{run_id}/{rest}", raw, source="frontend", mime=mime)
    else:
        node = request.app.state.store.put(f"/{run_id}/{rest}", body.content, source="user", mime=mime)
    return _node_dict(node)
