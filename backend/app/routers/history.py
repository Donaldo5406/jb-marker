"""[history] GET /runs/{run_id}/gallery · GET /runs/{run_id}/preview (spec §8.1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from ..history.gallery import build_gallery
from ..history.preview import build_preview_html
from ..schemas import ErrorOut, GalleryOut
from .deps import get_user_id, require_owner

router = APIRouter(tags=["history"])


@router.get("/runs/{run_id}/gallery", response_model=GalleryOut,
            summary="run 산출물 갤러리(스튜디오별 섹션)",
            responses={401: {"model": ErrorOut}, 404: {"model": ErrorOut}})
def get_gallery(run_id: str, request: Request,
                user_id: str = Depends(get_user_id)) -> dict:
    man = require_owner(request, run_id, user_id)
    nodes = request.app.state.store.list(f"/{run_id}")
    return build_gallery(man, nodes)


@router.get("/runs/{run_id}/preview", response_class=HTMLResponse,
            summary="디자인 시스템 셀프컨테인드 HTML 프리뷰",
            responses={401: {"model": ErrorOut}, 404: {"model": ErrorOut}})
def get_preview(run_id: str, request: Request,
                user_id: str = Depends(get_user_id)):
    require_owner(request, run_id, user_id)
    markup = build_preview_html(run_id, request.app.state.store)
    return HTMLResponse(content=markup)
