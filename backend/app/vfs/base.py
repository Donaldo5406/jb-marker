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

    @abstractmethod
    def list_runs(self, *, user_id: str = "demo") -> list[Manifest]: ...

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

    # --- 텍스트 편의 (deploy 라우트·DeployAdvisor·usage 로그의 정식 표면) ---
    # Local/Supabase가 문자 그대로 동일하게 복제하던 구현을 ABC 구체 메서드로 승격 (T1-P1).
    def put_text(self, path: str, content: str, *, source: str | None = None,
                 mime: str | None = None) -> VfsNode:
        return self.put(path, content, source=source or "marker", mime=mime)

    def get_text(self, path: str) -> str | None:
        n = self.get(path)
        return n.content_text if n else None
