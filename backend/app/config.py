"""런타임 설정 — env 로딩 (로컬-우선, 키 없어도 부팅)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """필수 설정 누락 — supabase 모드인데 키 부재 등."""


def _truthy(v: str | None) -> bool:
    return (v or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None
    openai_api_key: str | None
    google_api_key: str | None
    vfs_backend: str            # "local" | "supabase"
    entitlement_override: bool  # 데모용 유료 게이트 우회 (실 PG 청구 Non-goal)
    storage_dir: str            # 로컬 블롭 루트
    anthropic_model: str
    openai_model: str
    google_model: str
    # M6 advisor live-LLM 모드 — "auto"(키 있으면 live, 없으면 scripted) | "live" | "scripted"
    advisor_mode: str
    anthropic_advisor_model: str
    # LLM 출력 상한 — spec/plan 전체 문서를 JSON으로 담아야 해 2048은 절단됨(빈 산출물 원인). 기본 8192.
    # 기본값을 둬 직접 Settings(...) 생성(테스트 등) 호환 유지.
    anthropic_max_tokens: int = 8192
    # S2a 이미지(Nano Banana) 모델 — usage 기록·google_client 호출의 단일 출처.
    google_image_model: str = "gemini-2.5-flash-image"
    # M7-A Supabase
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_anon_key: str | None = None
    supabase_jwt_secret: str | None = None
    supabase_storage_bucket: str = "vfs-blobs"
    # M7-C 분리형 배포 — 명시 CORS origin 화이트리스트(쉼표 구분). 미설정 시 localhost 폴백.
    cors_allow_origins: tuple[str, ...] = ()
    # 세션 수명주기 임계(ms) — spec §3.5. 데모/테스트에서 단축 가능.
    session_stall_ms: int = 15 * 60 * 1000          # 900_000
    session_suspend_ms: int = 60 * 60 * 1000        # 3_600_000
    session_retention_ms: int = 7 * 24 * 60 * 60 * 1000  # 604_800_000


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        vfs_backend=os.getenv("VFS_BACKEND", "local"),
        entitlement_override=_truthy(os.getenv("ENTITLEMENT_OVERRIDE")),
        storage_dir=os.getenv("JBM_STORAGE_DIR", "data/runs"),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        google_model=os.getenv("GOOGLE_MODEL", "gemini-2.0-flash"),
        anthropic_max_tokens=int(os.getenv("ANTHROPIC_MAX_TOKENS", "8192")),
        google_image_model=os.getenv("GOOGLE_IMAGE_MODEL", "gemini-2.5-flash-image"),
        advisor_mode=os.getenv("ADVISOR_MODE", "auto").strip().lower() or "auto",
        anthropic_advisor_model=os.getenv("ANTHROPIC_ADVISOR_MODEL", "claude-sonnet-4-6"),
        supabase_url=os.getenv("SUPABASE_URL") or None,
        supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY") or None,
        supabase_anon_key=os.getenv("SUPABASE_ANON_KEY") or None,
        supabase_jwt_secret=os.getenv("SUPABASE_JWT_SECRET") or None,
        supabase_storage_bucket=os.getenv("SUPABASE_STORAGE_BUCKET", "vfs-blobs"),
        cors_allow_origins=tuple(
            o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if o.strip()
        ),
        session_stall_ms=int(os.getenv("SESSION_STALL_MS", str(15 * 60 * 1000))),
        session_suspend_ms=int(os.getenv("SESSION_SUSPEND_MS", str(60 * 60 * 1000))),
        session_retention_ms=int(os.getenv("SESSION_RETENTION_MS", str(7 * 24 * 60 * 60 * 1000))),
    )
