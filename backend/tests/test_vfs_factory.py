import pytest

from app.config import Settings
from app.vfs.factory import get_vfs_store
from app.vfs.local import LocalVfsStore


def _settings(backend: str) -> Settings:
    return Settings(
        anthropic_api_key=None, openai_api_key=None, google_api_key=None,
        vfs_backend=backend, entitlement_override=False, storage_dir="data/runs",
        anthropic_model="m", openai_model="m", google_model="m",
        advisor_mode="auto", anthropic_advisor_model="m",
    )


def test_factory_returns_local_by_default():
    assert isinstance(get_vfs_store(_settings("local")), LocalVfsStore)


def test_supabase_backend_missing_keys_raises():
    from app.config import ConfigError, load_settings
    from dataclasses import replace
    s = load_settings()
    s2 = replace(s, vfs_backend="supabase", supabase_url=None,
                 supabase_service_role_key=None)
    from app.vfs.factory import get_vfs_store
    with pytest.raises(ConfigError):
        get_vfs_store(s2)
