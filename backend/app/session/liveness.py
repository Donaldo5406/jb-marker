"""Liveness 파생 — claw-code session.rs heartbeat_at 차용(순수 함수). spec §3.4.

evaluate()는 suspend/archive 전이 시 rec를 in-place 갱신한다.
영속(_save)은 호출자(SessionStore) 책임 — 순수 분류는 부작용 없는 테스트가 가능.
"""
from __future__ import annotations

from dataclasses import dataclass

from .record import (
    SessionRecord,
    STATUS_ACTIVE, STATUS_SUSPENDED, STATUS_ARCHIVED,
)

# 보고용 liveness 어휘 (claw-code 4-way + 도메인 확장)
HEALTHY = "healthy"
STALLED = "stalled"
SUSPENDED = "suspended"
ARCHIVED = "archived"
TRANSPORT_DEAD = "transport_dead"

DEFAULT_STALL_MS = 15 * 60 * 1000          # 900_000
DEFAULT_SUSPEND_MS = 60 * 60 * 1000        # 3_600_000
DEFAULT_RETENTION_MS = 7 * 24 * 60 * 60 * 1000  # 604_800_000


@dataclass(frozen=True)
class Thresholds:
    stall_ms: int = DEFAULT_STALL_MS
    suspend_ms: int = DEFAULT_SUSPEND_MS
    retention_ms: int = DEFAULT_RETENTION_MS


def evaluate(rec: SessionRecord, now_ms: int, th: Thresholds,
             *, transport_alive: bool = True) -> str:
    """liveness 문자열 반환. active→suspended→archived 캐스케이드(단일 호출)."""
    if not transport_alive:
        return TRANSPORT_DEAD
    if rec.status == STATUS_ARCHIVED:
        return ARCHIVED

    if rec.status == STATUS_ACTIVE:
        idle = max(0, now_ms - rec.updated_at_ms)  # claw-code saturating_sub
        if idle >= th.suspend_ms:
            rec.status = STATUS_SUSPENDED
            rec.suspended_at_ms = rec.updated_at_ms
            # fall through → retention 검사
        elif idle >= th.stall_ms:
            return STALLED
        else:
            return HEALTHY

    if rec.status == STATUS_SUSPENDED:
        if rec.suspended_at_ms is not None and now_ms - rec.suspended_at_ms >= th.retention_ms:
            rec.status = STATUS_ARCHIVED
            return ARCHIVED
        return SUSPENDED

    return HEALTHY


def heartbeat_view(rec: SessionRecord, now_ms: int, th: Thresholds,
                   *, transport_alive: bool = True) -> dict:
    """UI 카운트다운용 파생 뷰. liveness + 절대시각 임계."""
    live = evaluate(rec, now_ms, th, transport_alive=transport_alive)
    expires_at = (rec.suspended_at_ms + th.retention_ms
                  if rec.suspended_at_ms is not None else None)
    return {
        "liveness": live,
        "status": rec.status,
        "warn_at": rec.updated_at_ms + th.stall_ms,
        "suspend_at": rec.updated_at_ms + th.suspend_ms,
        "expires_at": expires_at,
    }
