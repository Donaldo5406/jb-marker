"""VFS 핵심 타입 — vfs.md 스키마 / marker_api.md §1 매핑."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

STUDIOS = ("brainstorming", "design", "review", "deploy", "usage")
# 세션 수명주기 대상(usage 제외 — 산출 집계 뷰라 대화 세션 없음). spec §4.
LIFECYCLE_STUDIOS = ("brainstorming", "design", "review", "deploy")


@dataclass
class VfsNode:
    run_id: str
    path: str
    kind: str = "file"
    mime: str | None = None
    source: str | None = None          # research|user|gemini|marker
    content_text: str | None = None    # 텍스트면 채움
    blob_path: str | None = None       # 블롭이면 Storage/디스크 키
    blob: bytes | None = None          # get() 시 로드(서빙용)
    meta: dict[str, Any] = field(default_factory=dict)
    grounds: Any | None = None
    hash: str | None = None
    created_at: str | None = None


@dataclass
class Manifest:
    run_id: str
    user_id: str = "demo"
    title: str | None = None
    current_step: str | None = None
    step_status: dict[str, str] = field(default_factory=dict)
    languages: list[str] = field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None
