"""[session] run-scoped 세션 라이프사이클 4종 (spec §8.1).

# D4: 세션 4종은 UI 미연결(헤드리스 계약) — spec §8.1
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request

from .deps import get_user_id, require_owner

router = APIRouter(tags=["session"])


def _now_ms() -> int:
    return int(time.time() * 1000)


@router.get("/runs/{run_id}/session/{studio}")
def session_heartbeat(run_id: str, studio: str, request: Request,
                      user_id: str = Depends(get_user_id)) -> dict:
    require_owner(request, run_id, user_id)
    return request.app.state.session_store.heartbeat(run_id, studio, _now_ms())


@router.post("/runs/{run_id}/session/{studio}/resume")
def session_resume(run_id: str, studio: str, request: Request,
                   user_id: str = Depends(get_user_id)) -> dict:
    require_owner(request, run_id, user_id)
    return request.app.state.session_store.resume(run_id, studio, _now_ms())


@router.post("/runs/{run_id}/session/{studio}/suspend")
def session_suspend(run_id: str, studio: str, request: Request,
                    user_id: str = Depends(get_user_id)) -> dict:
    require_owner(request, run_id, user_id)
    return request.app.state.session_store.suspend(run_id, studio, _now_ms())


@router.get("/runs/{run_id}/sessions")
def session_list(run_id: str, request: Request,
                 user_id: str = Depends(get_user_id)) -> dict:
    require_owner(request, run_id, user_id)
    return request.app.state.session_store.list(run_id, _now_ms())
