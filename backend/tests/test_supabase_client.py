from __future__ import annotations

import pytest

from app.config import Settings
from app import supabase_client


def _settings(**kw) -> Settings:
    base = dict(
        anthropic_api_key=None, openai_api_key=None, google_api_key=None,
        vfs_backend="supabase", entitlement_override=False, storage_dir="data/runs",
        anthropic_model="m", openai_model="m", google_model="m",
        advisor_mode="auto", anthropic_advisor_model="m",
        supabase_url=None, supabase_service_role_key=None, supabase_anon_key=None,
        supabase_jwt_secret=None, supabase_storage_bucket="vfs-blobs",
    )
    base.update(kw)
    return Settings(**base)


def test_missing_keys_raises_config_error():
    from app.config import ConfigError
    with pytest.raises(ConfigError):
        supabase_client.build_service_client(_settings(supabase_url=None))
