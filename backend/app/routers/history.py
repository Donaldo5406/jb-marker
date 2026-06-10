"""[history] GET /runs/{run_id}/gallery · GET /runs/{run_id}/preview (spec §8.1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from ..history.gallery import build_gallery
from ..history.preview import build_preview_html
from .deps import get_user_id, require_owner

router = APIRouter(tags=["history"])


@router.get("/runs/{run_id}/gallery")
def get_gallery(run_id: str, request: Request,
                user_id: str = Depends(get_user_id)) -> dict:
    man = require_owner(request, run_id, user_id)
    nodes = request.app.state.store.list(f"/{run_id}")
    return build_gallery(man, nodes)


@router.get("/runs/{run_id}/preview")
def get_preview(run_id: str, request: Request,
                user_id: str = Depends(get_user_id)):
    require_owner(request, run_id, user_id)
    markup = build_preview_html(run_id, request.app.state.store)
    return Response(content=markup, media_type="text/html")
