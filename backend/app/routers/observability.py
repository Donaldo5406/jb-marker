"""[observability] GET /runs/{run_id}/usage (spec §8.1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..observability import usage as usage_log
from ..schemas import ErrorOut, UsageSummaryOut
from .deps import get_user_id, require_owner

router = APIRouter(tags=["observability"])


@router.get("/runs/{run_id}/usage", response_model=UsageSummaryOut,
            summary="run의 LLM/이미지 사용량 집계",
            responses={401: {"model": ErrorOut}, 404: {"model": ErrorOut}})
def get_usage(run_id: str, request: Request,
              user_id: str = Depends(get_user_id)) -> dict:
    require_owner(request, run_id, user_id)
    return usage_log.summarize(request.app.state.store, run_id=run_id)
