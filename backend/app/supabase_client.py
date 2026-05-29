"""service_role Supabase 클라이언트 빌더 (지연 import — 로컬-우선 부팅 보존)."""
from __future__ import annotations

from .config import ConfigError, Settings

_cache: dict = {}


def build_service_client(settings: Settings):
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise ConfigError(
            "VFS_BACKEND=supabase 인데 SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 부재")
    key = (settings.supabase_url, settings.supabase_service_role_key)
    if key not in _cache:
        from supabase import create_client  # 지연 import
        _cache[key] = create_client(settings.supabase_url,
                                    settings.supabase_service_role_key)
    return _cache[key]
