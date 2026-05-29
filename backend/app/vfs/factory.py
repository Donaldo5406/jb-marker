"""설정에 따라 VfsStore impl 선택 (벤더 스왑)."""
from __future__ import annotations

from pathlib import Path

from ..config import Settings
from .base import VfsStore
from .local import LocalVfsStore


def get_vfs_store(settings: Settings) -> VfsStore:
    if settings.vfs_backend == "supabase":
        from ..config import ConfigError
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise ConfigError(
                "VFS_BACKEND=supabase 인데 SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 부재")
        from .supabase import SupabaseVfsStore
        return SupabaseVfsStore(settings)
    return LocalVfsStore(storage_dir=settings.storage_dir)


def make_local_store(tmp_path: Path | str) -> LocalVfsStore:
    """테스트용 LocalVfsStore 팩토리 — tmp_path를 storage_dir로 사용."""
    return LocalVfsStore(storage_dir=str(tmp_path))
