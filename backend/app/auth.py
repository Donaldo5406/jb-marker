"""Supabase JWT 검증 + user_id 도출 (접근 A: 백엔드 강제).

로컬-우선: VFS_BACKEND≠supabase 또는 Auth 미설정이면 "demo".
supabase 모드(알고리즘 인지):
  - ES256/RS256/EdDSA(비대칭) → JWKS 로컬 검증(.well-known/jwks.json, PyJWKClient 캐시)
  - HS256 + JWT secret → 로컬 디코드(레거시)
  - 그 외 → /auth/v1/user 호출(API 폴백)
모든 검증 실패 → AuthError(401).
"""
from __future__ import annotations

from functools import lru_cache

import jwt
from fastapi import HTTPException, Request

from .config import Settings


class AuthError(HTTPException):
    def __init__(self, detail: str = "unauthorized") -> None:
        super().__init__(status_code=401, detail=detail)


def _strip_bearer(header: str | None) -> str | None:
    if not header:
        return None
    parts = header.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return header.strip() or None


@lru_cache(maxsize=8)
def _get_jwks_client(jwks_url: str) -> "jwt.PyJWKClient":
    """jwks_url별 PyJWKClient 캐시 — 요청마다 JWKS 재요청 방지."""
    return jwt.PyJWKClient(jwks_url)


def resolve_user_id(authorization: str | None, settings: Settings) -> str:
    # 로컬-우선 폴백
    if settings.vfs_backend != "supabase" or not settings.supabase_url:
        return "demo"
    token = _strip_bearer(authorization)
    if not token:
        raise AuthError("missing bearer token")

    # 토큰 알고리즘 식별(서명 검증 없이 헤더만)
    try:
        alg = jwt.get_unverified_header(token).get("alg", "")
    except Exception as e:  # noqa: BLE001
        raise AuthError(f"bad token header: {e}") from e

    # 1) 비대칭(ES*/RS*/EdDSA) → JWKS 로컬 검증
    if alg.startswith("ES") or alg.startswith("RS") or alg == "EdDSA":
        jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        try:
            client = _get_jwks_client(jwks_url)
            signing_key = client.get_signing_key_from_jwt(token)
            payload = jwt.decode(token, signing_key.key,
                                 algorithms=[alg], audience="authenticated")
        except Exception as e:  # noqa: BLE001 — 모든 검증 실패는 401로 단일화
            raise AuthError(f"jwks verify failed: {e}") from e
        sub = payload.get("sub")
        if not sub:
            raise AuthError("jwt missing sub")
        return sub

    # 2) HS256 + secret → 로컬 디코드(레거시)
    if alg == "HS256" and settings.supabase_jwt_secret:
        try:
            payload = jwt.decode(token, settings.supabase_jwt_secret,
                                 algorithms=["HS256"], audience="authenticated")
        except Exception as e:  # noqa: BLE001 — 모든 검증 실패는 401로 단일화
            raise AuthError(f"jwt verify failed: {e}") from e
        sub = payload.get("sub")
        if not sub:
            raise AuthError("jwt missing sub")
        return sub

    # 3) 그 외 → Supabase auth API로 검증(API 폴백)
    import httpx
    try:
        r = httpx.get(f"{settings.supabase_url}/auth/v1/user",
                      headers={"Authorization": f"Bearer {token}",
                               "apikey": settings.supabase_anon_key or ""},
                      timeout=10.0)
    except Exception as e:  # noqa: BLE001
        raise AuthError(f"auth api unreachable: {e}") from e
    if r.status_code != 200:
        raise AuthError("auth api rejected token")
    uid = r.json().get("id")
    if not uid:
        raise AuthError("auth api returned no id")
    return uid


def make_user_id_dep(settings: Settings):
    """server.create_app에서 settings를 클로저로 묶어 의존성 생성."""
    def _dep(request: Request) -> str:
        return resolve_user_id(request.headers.get("authorization"), settings)
    return _dep
