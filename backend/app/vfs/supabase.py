"""SupabaseVfsStore — Postgres(runs/vfs_nodes) + Storage 블롭 (M7-A).

service_role 클라이언트로 접근. 소유권 강제는 라우트 가드(require_run_owner)가 담당.
불변식(LocalVfsStore 계약): ① 미디어 put → meta 동시기록 ② 스텝전환 → manifest 갱신.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from ..config import Settings
from .base import VfsStore
from .paths import validate_path
from .types import Manifest, VfsNode, STUDIOS


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_id_of(path: str) -> str:
    return path.strip("/").split("/", 1)[0]


class SupabaseVfsStore(VfsStore):
    def __init__(self, settings: Settings) -> None:
        from ..supabase_client import build_service_client
        self._sb = build_service_client(settings)
        self._bucket = settings.supabase_storage_bucket

    # --- 직렬화 헬퍼 ---
    def _manifest_from_row(self, row: dict) -> Manifest:
        return Manifest(
            run_id=row["run_id"], user_id=row.get("user_id") or "demo",
            title=row.get("title"), current_step=row.get("current_step"),
            step_status=row.get("step_status") or {},
            languages=row.get("languages") or [],
            created_at=row.get("created_at"), updated_at=row.get("updated_at"))

    def _node_from_row(self, row: dict) -> VfsNode:
        return VfsNode(
            run_id=row["run_id"], path=row["path"], kind=row.get("kind") or "file",
            mime=row.get("mime"), source=row.get("source"),
            content_text=row.get("content_text"), blob_path=row.get("blob_path"),
            meta=row.get("meta") or {}, grounds=row.get("grounds"),
            hash=row.get("hash"), created_at=row.get("created_at"))

    # --- run 메타 ---
    def create_run(self, run_id, *, user_id="demo", title=None, languages=None) -> Manifest:
        row = {"run_id": run_id, "user_id": user_id, "title": title,
               "step_status": {}, "languages": list(languages or []),
               "created_at": _now(), "updated_at": _now()}
        self._sb.table("runs").insert(row).execute()
        return self._manifest_from_row(row)

    def get_manifest(self, run_id) -> Manifest | None:
        res = self._sb.table("runs").select("*").eq("run_id", run_id).limit(1).execute()
        return self._manifest_from_row(res.data[0]) if res.data else None

    def patch_manifest(self, run_id, patch) -> Manifest:
        if self.get_manifest(run_id) is None:
            raise KeyError(run_id)
        patch = {**patch, "updated_at": _now()}
        res = self._sb.table("runs").update(patch).eq("run_id", run_id).execute()
        return self._manifest_from_row(res.data[0])

    def set_step_status(self, run_id, step, status) -> Manifest:
        if step not in STUDIOS:
            raise ValueError(f"알 수 없는 step {step!r} (허용: {STUDIOS})")
        m = self.get_manifest(run_id)
        if m is None:
            raise KeyError(run_id)
        m.step_status[step] = status
        patch = {"step_status": m.step_status, "current_step": step, "updated_at": _now()}
        res = self._sb.table("runs").update(patch).eq("run_id", run_id).execute()
        return self._manifest_from_row(res.data[0])

    def list_runs(self, *, user_id="demo") -> list[Manifest]:
        res = (self._sb.table("runs").select("*").eq("user_id", user_id)
               .order("created_at", desc=True).execute())
        return [self._manifest_from_row(r) for r in res.data]

    # --- 노드 CRUD (텍스트; 블롭은 Task 6) ---
    def put(self, path, content, *, meta=None, source=None, mime=None) -> VfsNode:
        validate_path(path)
        run_id = _run_id_of(path)
        if isinstance(content, bytes):
            return self._put_blob(path, run_id, content, meta=meta, source=source, mime=mime)
        node = VfsNode(run_id=run_id, path=path, mime=mime, source=source,
                       content_text=content, meta=dict(meta or {}),
                       hash=hashlib.sha256(content.encode()).hexdigest(), created_at=_now())
        self._upsert_node(node)
        return node

    def _upsert_node(self, node: VfsNode) -> None:
        row = {"run_id": node.run_id, "path": node.path, "kind": node.kind,
               "mime": node.mime, "source": node.source,
               "content_text": node.content_text, "blob_path": node.blob_path,
               "meta": node.meta or {}, "grounds": node.grounds,
               "hash": node.hash, "created_at": node.created_at or _now()}
        self._sb.table("vfs_nodes").upsert(row, on_conflict="run_id,path").execute()

    def get(self, path) -> VfsNode | None:
        run_id = _run_id_of(path)
        res = (self._sb.table("vfs_nodes").select("*")
               .eq("run_id", run_id).eq("path", path).limit(1).execute())
        if not res.data:
            return None
        node = self._node_from_row(res.data[0])
        if node.blob_path:
            node.blob = self._download_blob(node.blob_path)
        return node

    def read_meta(self, path) -> dict | None:
        run_id = _run_id_of(path)
        res = (self._sb.table("vfs_nodes").select("meta")
               .eq("run_id", run_id).eq("path", path).limit(1).execute())
        return (res.data[0]["meta"] or {}) if res.data else None

    def list(self, prefix) -> list[VfsNode]:
        p = prefix.rstrip("/")
        run_id = _run_id_of(p)
        res = (self._sb.table("vfs_nodes").select("*")
               .eq("run_id", run_id)
               .or_(f"path.eq.{p},path.like.{p}/%").execute())
        return [self._node_from_row(r) for r in res.data]

    def update(self, path, patch) -> VfsNode:
        node = self.get(path)
        if node is None:
            raise KeyError(path)
        run_id = _run_id_of(path)
        self._sb.table("vfs_nodes").update(patch).eq("run_id", run_id).eq("path", path).execute()
        for k, v in patch.items():
            setattr(node, k, v)
        return node

    def delete(self, path) -> None:
        run_id = _run_id_of(path)
        self._sb.table("vfs_nodes").delete().eq("run_id", run_id).eq("path", path).execute()

    # --- 블롭 (Storage) ---
    def _put_blob(self, path, run_id, content, *, meta, source, mime):
        digest = hashlib.sha256(content).hexdigest()
        blob_key = f"{run_id}/{digest}.bin"
        self._sb.storage.from_(self._bucket).upload(
            blob_key, content,
            {"content-type": mime or "application/octet-stream", "upsert": "true"})
        node = VfsNode(run_id=run_id, path=path, mime=mime, source=source,
                       blob_path=blob_key, hash=digest,
                       meta=dict(meta or {}), created_at=_now())
        # 불변식: 미디어 put → meta 동시기록
        if not node.meta:
            kind = "image" if (mime or "").startswith("image/") else (
                "video" if (mime or "").startswith("video/") else "file")
            node.meta = {"type": kind, "source": source, "mime": mime}
        else:
            node.meta.setdefault("source", source)
            node.meta.setdefault("mime", mime)
        self._upsert_node(node)
        node.blob = content
        return node

    def _download_blob(self, blob_path: str) -> bytes:
        return self._sb.storage.from_(self._bucket).download(blob_path)

    def create_signed_url(self, path: str, *, expires_in: int = 3600) -> str | None:
        """블롭 노드의 만료 서명 URL (M7-B History 뷰어용). 텍스트/부재 시 None."""
        run_id = _run_id_of(path)
        res = (self._sb.table("vfs_nodes").select("blob_path")
               .eq("run_id", run_id).eq("path", path).limit(1).execute())
        if not res.data or not res.data[0].get("blob_path"):
            return None
        signed = self._sb.storage.from_(self._bucket).create_signed_url(
            res.data[0]["blob_path"], expires_in)
        return signed.get("signedURL") or signed.get("signed_url")
