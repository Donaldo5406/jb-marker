"""[history] GET /runs/{run_id}/gallery · GET /runs/{run_id}/preview
· GET /runs/{run_id}/review-highlight (spec §8.1)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from ..gateway.review_highlight import build_highlight_html, collect_rects
from ..history.gallery import build_gallery
from ..history.preview import _blob_bytes, _downscale_inline, build_preview_html
from ..schemas import GalleryOut, OWNER_RESPONSES
from .deps import get_user_id, require_owner

router = APIRouter(tags=["history"])


@router.get("/runs/{run_id}/gallery", response_model=GalleryOut,
            summary="run 산출물 갤러리(스튜디오별 섹션)",
            responses=OWNER_RESPONSES)
def get_gallery(run_id: str, request: Request,
                user_id: str = Depends(get_user_id)) -> dict:
    man = require_owner(request, run_id, user_id)
    nodes = request.app.state.store.list(f"/{run_id}")
    return build_gallery(man, nodes)


@router.get("/runs/{run_id}/preview", response_class=HTMLResponse,
            summary="디자인 시스템 셀프컨테인드 HTML 프리뷰",
            responses=OWNER_RESPONSES)
def get_preview(run_id: str, request: Request,
                user_id: str = Depends(get_user_id)):
    require_owner(request, run_id, user_id)
    markup = build_preview_html(run_id, request.app.state.store)
    return HTMLResponse(content=markup)


@router.get("/runs/{run_id}/review-highlight", response_class=HTMLResponse,
            summary="리뷰 포스터 하이라이트 오버레이(셀프컨테인드 HTML)",
            responses=OWNER_RESPONSES)
def get_review_highlight(run_id: str, image: str, request: Request,
                         user_id: str = Depends(get_user_id)):
    require_owner(request, run_id, user_id)
    store = request.app.state.store
    node = store.get(f"/{run_id}/{image}")
    if node is None:
        # 이미지 없음(폴백) — 빈 rects로 이미지 없는 HTML 반환.
        return HTMLResponse(content=build_highlight_html(b"", "image/png", []))
    raw = _blob_bytes(node)
    small, mime = _downscale_inline(raw, node.mime, max_dim=720)
    verdicts: list[dict] = []
    for n in store.list(f"/{run_id}/review"):
        if n.path.endswith("/verdict.json") and n.content_text:
            try:
                verdicts.append(json.loads(n.content_text))
            except Exception:
                pass
    rects = collect_rects(verdicts, image)
    return HTMLResponse(content=build_highlight_html(small, mime, rects))
