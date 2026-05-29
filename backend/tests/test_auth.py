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


# --- ES256 (JWKS 비대칭) 검증 ---------------------------------------------

def _gen_ec_keypair():
    """EC P-256 키페어 생성 → (private_pem_str, public_key_obj)."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    priv = ec.generate_private_key(ec.SECP256R1())
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    return priv_pem, priv.public_key()


class _FakeJWKClient:
    """PyJWKClient 대체: 미리 정해둔 public key를 반환."""

    def __init__(self, public_key):
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token):  # noqa: ARG002 — 시그니처만 모방
        class _Key:
            def __init__(self, key):
                self.key = key

        return _Key(self._public_key)


def test_es256_jwks_path_extracts_sub(monkeypatch):
    priv_pem, pub_key = _gen_ec_keypair()
    s = _settings(vfs_backend="supabase", supabase_url="https://x.supabase.co",
                  supabase_jwt_secret=None)
    token = jwt.encode({"sub": "user-es256", "aud": "authenticated"},
                       priv_pem, algorithm="ES256")
    # 모듈 레벨 JWKS 클라이언트를 가짜로 치환 → public key 직접 반환
    monkeypatch.setattr(auth, "_get_jwks_client",
                        lambda url: _FakeJWKClient(pub_key))
    assert auth.resolve_user_id(f"Bearer {token}", s) == "user-es256"


def test_es256_jwks_path_rejects_bad_signature(monkeypatch):
    # 토큰은 키 A로 서명, 검증은 키 B의 public key로 → 서명 불일치
    priv_pem_a, _pub_a = _gen_ec_keypair()
    _priv_pem_b, pub_b = _gen_ec_keypair()
    s = _settings(vfs_backend="supabase", supabase_url="https://x.supabase.co",
                  supabase_jwt_secret=None)
    token = jwt.encode({"sub": "u", "aud": "authenticated"},
                       priv_pem_a, algorithm="ES256")
    monkeypatch.setattr(auth, "_get_jwks_client",
                        lambda url: _FakeJWKClient(pub_b))
    with pytest.raises(auth.AuthError):
        auth.resolve_user_id(f"Bearer {token}", s)


def test_es256_jwks_path_missing_sub_raises(monkeypatch):
    priv_pem, pub_key = _gen_ec_keypair()
    s = _settings(vfs_backend="supabase", supabase_url="https://x.supabase.co",
                  supabase_jwt_secret=None)
    token = jwt.encode({"aud": "authenticated"}, priv_pem, algorithm="ES256")
    monkeypatch.setattr(auth, "_get_jwks_client",
                        lambda url: _FakeJWKClient(pub_key))
    with pytest.raises(auth.AuthError):
        auth.resolve_user_id(f"Bearer {token}", s)


def test_get_jwks_client_caches_per_url(monkeypatch):
    """_get_jwks_client는 같은 URL에 대해 PyJWKClient를 1회만 생성(캐시)."""
    calls = []

    class _Stub:
        def __init__(self, url):
            calls.append(url)

    monkeypatch.setattr(auth.jwt, "PyJWKClient", _Stub)
    auth._get_jwks_client.cache_clear()
    url = "https://x.supabase.co/auth/v1/.well-known/jwks.json"
    c1 = auth._get_jwks_client(url)
    c2 = auth._get_jwks_client(url)
    assert c1 is c2
    assert calls == [url]  # 2번째 호출은 캐시 히트라 생성 안 됨
    auth._get_jwks_client.cache_clear()
