"""SessionRecord — (run_id, studio) 세션 수명주기 봉투. spec §3.1."""
from __future__ import annotations

import json
from dataclasses import dataclass

SESSION_VERSION = 1
STATUS_ACTIVE = "active"
STATUS_SUSPENDED = "suspended"
STATUS_ARCHIVED = "archived"


def derive_session_id(run_id: str, studio: str) -> str:
    return f"sess_{run_id}_{studio}"


def session_path(run_id: str, studio: str) -> str:
    return f"/{run_id}/{studio}/_session.json"


@dataclass
class SessionRecord:
    run_id: str
    studio: str
    created_at_ms: int
    updated_at_ms: int
    status: str = STATUS_ACTIVE
    suspended_at_ms: int | None = None
    last_activity_kind: str = "user_turn"
    version: int = SESSION_VERSION

    @classmethod
    def new(cls, run_id: str, studio: str, now_ms: int) -> "SessionRecord":
        return cls(run_id=run_id, studio=studio,
                   created_at_ms=now_ms, updated_at_ms=now_ms)

    @property
    def session_id(self) -> str:
        return derive_session_id(self.run_id, self.studio)

    def to_json(self) -> str:
        return json.dumps({
            "version": self.version,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "studio": self.studio,
            "created_at_ms": self.created_at_ms,
            "updated_at_ms": self.updated_at_ms,
            "status": self.status,
            "suspended_at_ms": self.suspended_at_ms,
            "last_activity_kind": self.last_activity_kind,
        }, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> "SessionRecord":
        d = json.loads(text)
        return cls(
            run_id=d["run_id"],
            studio=d["studio"],
            created_at_ms=int(d["created_at_ms"]),
            updated_at_ms=int(d["updated_at_ms"]),
            status=d.get("status", STATUS_ACTIVE),
            suspended_at_ms=d.get("suspended_at_ms"),
            last_activity_kind=d.get("last_activity_kind", "user_turn"),
            version=int(d.get("version", SESSION_VERSION)),
        )
