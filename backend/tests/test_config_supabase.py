from __future__ import annotations

import app.config as config


def test_settings_reads_supabase_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "svc")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "")
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "vfs-blobs")
    s = config.load_settings()
    assert s.supabase_url == "https://x.supabase.co"
    assert s.supabase_service_role_key == "svc"
    assert s.supabase_anon_key == "anon"
    assert s.supabase_jwt_secret is None  # 빈 문자열 → None
    assert s.supabase_storage_bucket == "vfs-blobs"


def test_settings_storage_bucket_default(monkeypatch):
    monkeypatch.delenv("SUPABASE_STORAGE_BUCKET", raising=False)
    s = config.load_settings()
    assert s.supabase_storage_bucket == "vfs-blobs"
