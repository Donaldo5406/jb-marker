"""SessionStore — VfsStore 위 세션 수명주기 영속/조회. spec §3.2,§5,§6.

now_ms는 항상 호출자가 주입(claw-code heartbeat_at 패턴) → 결정론 단위 테스트.
서버는 실시계(int(time.time()*1000))를 넘긴다.
"""
from __future__ import annotations

from ..vfs.base import VfsStore
from ..vfs.types import LIFECYCLE_STUDIOS
from .record import (
    SessionRecord, session_path,
    STATUS_ACTIVE, STATUS_SUSPENDED, STATUS_ARCHIVED,
)
from .liveness import Thresholds, evaluate, heartbeat_view, ARCHIVED


class SessionStore:
    def __init__(self, vfs: VfsStore, thresholds: Thresholds | None = None) -> None:
        self._vfs = vfs
        self._th = thresholds or Thresholds()

    # --- 영속 I/O ---
    def _load(self, run_id: str, studio: str) -> SessionRecord | None:
        n = self._vfs.get(session_path(run_id, studio))
        if n and n.content_text:
            return SessionRecord.from_json(n.content_text)
        return None

    def _save(self, rec: SessionRecord) -> None:
        self._vfs.put(session_path(rec.run_id, rec.studio), rec.to_json(),
                      source="marker", mime="application/json")

    # --- 쓰기 측 ---
    def get_or_create(self, run_id: str, studio: str, now_ms: int) -> SessionRecord:
        rec = self._load(run_id, studio)
        if rec is None:  # backfill (spec §9) — 레거시 run도 안 깨짐
            rec = SessionRecord.new(run_id, studio, now_ms)
            self._save(rec)
        return rec

    def touch(self, run_id: str, studio: str, now_ms: int,
              *, kind: str = "user_turn") -> SessionRecord:
        rec = self.get_or_create(run_id, studio, now_ms)
        rec.status = STATUS_ACTIVE
        rec.suspended_at_ms = None
        rec.updated_at_ms = now_ms
        rec.last_activity_kind = kind
        self._save(rec)
        return rec

    # --- 읽기 측 (lazy 전이는 영속) ---
    def heartbeat(self, run_id: str, studio: str, now_ms: int,
                  *, transport_alive: bool = True) -> dict:
        rec = self._load(run_id, studio)
        if rec is None:
            return {"kind": "heartbeat", "exists": False,
                    "status": None, "resumable": False}
        before = rec.status
        view = heartbeat_view(rec, now_ms, self._th, transport_alive=transport_alive)
        if rec.status != before:  # active→suspended/archived lazy 전이 영속
            self._save(rec)
        view.update(kind="heartbeat", exists=True,
                    resumable=(rec.status != STATUS_ARCHIVED))
        return view

    def list(self, run_id: str, now_ms: int) -> dict:
        sessions = []
        for studio in LIFECYCLE_STUDIOS:
            rec = self._load(run_id, studio)
            if rec is None:
                continue
            before = rec.status
            view = heartbeat_view(rec, now_ms, self._th)
            if rec.status != before:
                self._save(rec)
            sessions.append({
                "studio": studio,
                "status": rec.status,
                "updated_at_ms": rec.updated_at_ms,
                "expires_at": view["expires_at"],
            })
        return {"kind": "session_list", "sessions": sessions}

    # --- 전이 측 ---
    def resume(self, run_id: str, studio: str, now_ms: int) -> dict:
        rec = self._load(run_id, studio)
        if rec is None:
            return {"kind": "expired", "reason": "no_session"}
        live = evaluate(rec, now_ms, self._th)  # 캐스케이드(archived 판정 포함)
        if live == ARCHIVED:
            self._save(rec)  # archived 전이 영속
            return {"kind": "expired", "reason": "retention_elapsed"}
        self.touch(run_id, studio, now_ms, kind="resume")  # 재수화 → active
        return {"kind": "restored", "run_id": run_id, "studio": studio, "status": "active"}

    def suspend(self, run_id: str, studio: str, now_ms: int) -> dict:
        rec = self.get_or_create(run_id, studio, now_ms)
        if rec.status == STATUS_ACTIVE:
            rec.status = STATUS_SUSPENDED
            rec.suspended_at_ms = now_ms
            self._save(rec)
        return {"kind": "suspended", "status": rec.status}
