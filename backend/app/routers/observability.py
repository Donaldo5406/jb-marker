"""[observability] GET /runs/{run_id}/usage (spec §8.1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..observability import usage as usage_log
from .deps import get_user_id, require_owner

router = APIRouter(tags=["observability"])


@router.get("/runs/{run_id}/usage")
def get_usage(run_id: str, request: Request,
              user_id: str = Depends(get_user_id)) -> dict:
    require_owner(request, run_id, user_id)
    return usage_log.summarize(request.app.state.store, run_id=run_id)
