"""설정에 따라 VfsStore impl 선택 (벤더 스왑)."""
from __future__ import annotations

from ..config import Settings
from .base import VfsStore
from .local import LocalVfsStore


def get_vfs_store(settings: Settings) -> VfsStore:
    if settings.vfs_backend == "supabase":
        from .supabase import SupabaseVfsStore
        return SupabaseVfsStore()
    return LocalVfsStore(storage_dir=settings.storage_dir)
