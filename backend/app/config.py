"""런타임 설정 — env 로딩 (로컬-우선, 키 없어도 부팅)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


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
        advisor_mode=os.getenv("ADVISOR_MODE", "auto").strip().lower() or "auto",
        anthropic_advisor_model=os.getenv("ANTHROPIC_ADVISOR_MODEL", "claude-sonnet-4-6"),
    )
