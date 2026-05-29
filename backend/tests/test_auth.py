from __future__ import annotations

from dataclasses import replace

import jwt
import pytest

from app.config import load_settings
from app import auth


def _settings(**kw):
    return replace(load_settings(), **kw)


def test_local_mode_returns_demo():
    s = _settings(vfs_backend="local")
    assert auth.resolve_user_id(None, s) == "demo"


def test_supabase_mode_missing_token_raises_401():
    s = _settings(vfs_backend="supabase", supabase_url="https://x.supabase.co",
                  supabase_service_role_key="svc", supabase_jwt_secret="sec")
    with pytest.raises(auth.AuthError):
        auth.resolve_user_id(None, s)


def test_jwt_secret_path_extracts_sub():
    s = _settings(vfs_backend="supabase", supabase_url="https://x.supabase.co",
                  supabase_service_role_key="svc", supabase_jwt_secret="sec")
    token = jwt.encode({"sub": "user-123", "aud": "authenticated"}, "sec", algorithm="HS256")
    assert auth.resolve_user_id(f"Bearer {token}", s) == "user-123"


def test_jwt_secret_path_rejects_bad_signature():
    s = _settings(vfs_backend="supabase", supabase_url="https://x.supabase.co",
                  supabase_service_role_key="svc", supabase_jwt_secret="sec")
    bad = jwt.encode({"sub": "u", "aud": "authenticated"}, "WRONG", algorithm="HS256")
    with pytest.raises(auth.AuthError):
        auth.resolve_user_id(f"Bearer {bad}", s)
