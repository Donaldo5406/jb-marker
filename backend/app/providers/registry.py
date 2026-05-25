"""이름 → Provider 인스턴스 (settings로 키/모델 주입)."""
from __future__ import annotations

from ..config import Settings
from .base import Provider
from .fake import FakeProvider


def get_provider(name: str, settings: Settings | None = None) -> Provider:
    if name == "fake":
        return FakeProvider()
    if name == "anthropic":
        from .anthropic_client import AnthropicProvider
        return AnthropicProvider(settings.anthropic_api_key if settings else None)
    if name == "openai":
        from .openai_client import OpenAIProvider
        return OpenAIProvider(settings.openai_api_key if settings else None)
    if name == "google":
        from .google_client import GoogleProvider
        return GoogleProvider(settings.google_api_key if settings else None)
    raise ValueError(f"알 수 없는 provider: {name!r}")
