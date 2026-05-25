"""VfsStore 추상 인터페이스 — 3 하네스 공유 CRUD 스킬의 계약 (marker_api.md §3-1)."""
from __future__ import annotations

from abc import ABC, abstractmethod

from .types import Manifest, VfsNode


class VfsStore(ABC):
    # --- run 메타 ---
    @abstractmethod
    def create_run(self, run_id: str, *, user_id: str = "demo",
                   title: str | None = None, languages: list[str] | None = None) -> Manifest: ...

    @abstractmethod
    def get_manifest(self, run_id: str) -> Manifest | None: ...

    @abstractmethod
    def patch_manifest(self, run_id: str, patch: dict) -> Manifest: ...

    @abstractmethod
    def set_step_status(self, run_id: str, step: str, status: str) -> Manifest: ...

    # --- 노드 CRUD ---
    @abstractmethod
    def put(self, path: str, content: str | bytes, *, meta: dict | None = None,
            source: str | None = None, mime: str | None = None) -> VfsNode: ...

    @abstractmethod
    def get(self, path: str) -> VfsNode | None: ...

    @abstractmethod
    def read_meta(self, path: str) -> dict | None: ...

    @abstractmethod
    def list(self, prefix: str) -> list[VfsNode]: ...

    @abstractmethod
    def update(self, path: str, patch: dict) -> VfsNode: ...

    @abstractmethod
    def delete(self, path: str) -> None: ...
