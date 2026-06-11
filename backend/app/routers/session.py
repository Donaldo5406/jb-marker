"""[session] run-scoped 세션 라이프사이클 4종 (spec §8.1).

# D4: 세션 4종은 UI 미연결(헤드리스 계약) — spec §8.1
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request

from ..schemas import (
    OWNER_RESPONSES,
    SessionExpiredOut,
    SessionListOut,
    SessionLivenessOut,
    SessionMissingOut,
    SessionRestoredOut,
    SessionSuspendOut,
)
from .deps import get_user_id, require_owner

router = APIRouter(tags=["session"])


def _now_ms() -> int:
    return int(time.time() * 1000)


# exists Literal(True/False)이 배타 판별 — 순서 비의존(smart union).
# "있음" 8키 dict는 Liveness(exists=True)로, "없음" 4키 dict는
# Missing(exists=False)으로 구조적으로 매칭(정확 키셋 wire 보존).
@router.get("/runs/{run_id}/session/{studio}",
            response_model=SessionLivenessOut | SessionMissingOut,
            summary="세션 하트비트 — liveness 파생 뷰",
            responses=OWNER_RESPONSES)
def session_heartbeat(run_id: str, studio: str, request: Request,
                      user_id: str = Depends(get_user_id)) -> dict:
    require_owner(request, run_id, user_id)
    return request.app.state.session_store.heartbeat(run_id, studio, _now_ms())


@router.post("/runs/{run_id}/session/{studio}/resume",
             response_model=SessionRestoredOut | SessionExpiredOut,
             summary="세션 재개 — archived면 expired 응답",
             responses=OWNER_RESPONSES)
def session_resume(run_id: str, studio: str, request: Request,
                   user_id: str = Depends(get_user_id)) -> dict:
    require_owner(request, run_id, user_id)
    return request.app.state.session_store.resume(run_id, studio, _now_ms())


@router.post("/runs/{run_id}/session/{studio}/suspend",
             response_model=SessionSuspendOut,
             summary="세션 명시 종료(suspend)",
             responses=OWNER_RESPONSES)
def session_suspend(run_id: str, studio: str, request: Request,
                    user_id: str = Depends(get_user_id)) -> dict:
    require_owner(request, run_id, user_id)
    return request.app.state.session_store.suspend(run_id, studio, _now_ms())


@router.get("/runs/{run_id}/sessions",
            response_model=SessionListOut,
            summary="run의 스튜디오별 세션 목록",
            responses=OWNER_RESPONSES)
def session_list(run_id: str, request: Request,
                 user_id: str = Depends(get_user_id)) -> dict:
    require_owner(request, run_id, user_id)
    return request.app.state.session_store.list(run_id, _now_ms())
