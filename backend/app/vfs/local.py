"""LocalVfsStore — 인메모리 인덱스 + 디스크 블롭 (오프라인·테스트·데모).

storage.py env-스왑 패턴 계승: JBM_STORAGE_DIR로 블롭 루트 지정.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

from .base import VfsStore
from .paths import parse_path, validate_path
from .types import Manifest, VfsNode, STUDIOS


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LocalVfsStore(VfsStore):
    def __init__(self, storage_dir: str | None = None) -> None:
        self._nodes: dict[str, VfsNode] = {}
        self._manifests: dict[str, Manifest] = {}
        self._storage_dir = storage_dir

    def _blob_root(self) -> Path:
        return Path(self._storage_dir or os.environ.get("JBM_STORAGE_DIR") or "data/runs")

    # --- run 메타 (Task 9에서 본격 구현; 텍스트 테스트용 최소) ---
    def create_run(self, run_id, *, user_id="demo", title=None, languages=None) -> Manifest:
        m = Manifest(run_id=run_id, user_id=user_id, title=title,
                     languages=list(languages or []), created_at=_now(), updated_at=_now())
        self._manifests[run_id] = m
        return m

    def get_manifest(self, run_id) -> Manifest | None:
        return self._manifests.get(run_id)

    def patch_manifest(self, run_id, patch) -> Manifest:
        m = self._manifests.get(run_id)
        if m is None:
            raise KeyError(run_id)
        for k, v in patch.items():
            setattr(m, k, v)
        m.updated_at = _now()
        return m

    def set_step_status(self, run_id, step, status) -> Manifest:
        if step not in STUDIOS:
            raise ValueError(f"알 수 없는 step {step!r} (허용: {STUDIOS})")
        m = self._manifests.get(run_id)
        if m is None:
            raise KeyError(run_id)
        m.step_status[step] = status
        m.current_step = step          # 불변식: 스텝전환 → current_step 동기
        m.updated_at = _now()
        return m

    def list_runs(self, *, user_id="demo") -> list[Manifest]:
        ms = [m for m in self._manifests.values() if m.user_id == user_id]
        return sorted(ms, key=lambda m: m.created_at or "", reverse=True)

    # --- 노드 CRUD ---
    def put(self, path, content, *, meta=None, source=None, mime=None) -> VfsNode:
        validate_path(path)
        run_id, _, _ = parse_path(path)
        is_blob = isinstance(content, bytes)
        node = VfsNode(run_id=run_id, path=path, mime=mime, source=source,
                       meta=dict(meta or {}), created_at=_now())
        if is_blob:
            digest = hashlib.sha256(content).hexdigest()
            root = self._blob_root() / run_id
            root.mkdir(parents=True, exist_ok=True)
            blob_file = root / f"{digest}.bin"
            blob_file.write_bytes(content)
            node.blob_path = str(blob_file)
            node.hash = digest
            # 불변식: 미디어 put → meta 동시기록 (없으면 자동생성)
            if not node.meta:
                kind = "image" if (mime or "").startswith("image/") else (
                    "video" if (mime or "").startswith("video/") else "file")
                node.meta = {"type": kind, "source": source, "mime": mime}
            else:
                node.meta.setdefault("source", source)
                node.meta.setdefault("mime", mime)
            self._nodes[path] = node
            return node
        node.content_text = content
        node.hash = hashlib.sha256(content.encode()).hexdigest()
        self._nodes[path] = node
        return node

    def get(self, path) -> VfsNode | None:
        n = self._nodes.get(path)
        if n and n.blob_path and n.blob is None:
            p = Path(n.blob_path)
            if p.exists():
                n.blob = p.read_bytes()
        return n

    def read_meta(self, path) -> dict | None:
        n = self._nodes.get(path)
        return n.meta if n else None

    def list(self, prefix) -> list[VfsNode]:
        p = prefix.rstrip("/")
        return [n for path, n in self._nodes.items() if path == p or path.startswith(p + "/")]

    def update(self, path, patch) -> VfsNode:
        n = self._nodes.get(path)
        if n is None:
            raise KeyError(path)
        for k, v in patch.items():
            setattr(n, k, v)
        return n

    def delete(self, path) -> None:
        self._nodes.pop(path, None)

    # --- 편의 메서드 (M6 deploy 라우트·AdvisorHarness용) ---
    def put_text(self, path: str, content: str, *, source: str | None = None,
                 mime: str | None = None) -> VfsNode:
        return self.put(path, content, source=source or "marker", mime=mime)

    def get_text(self, path: str) -> str | None:
        n = self.get(path)
        return n.content_text if n else None
