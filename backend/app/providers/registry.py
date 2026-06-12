"""이름 → Provider 인스턴스 (settings로 키/모델 주입)."""
from __future__ import annotations

from ..config import Settings
from .base import Provider
from .fake import FakeProvider

# provider 어휘 SSOT — GatewayRun.provider Literal(routers/gateway.py)과 양방향 동기
# (tests/test_openapi_contract.py). get_provider if-체인 분기를 더하거나 빼면 함께 갱신할 것.
PROVIDER_NAMES = ("fake", "demo", "anthropic", "openai", "google")


def get_provider(name: str, settings: Settings | None = None) -> Provider:
    if name == "fake":
        return FakeProvider()
    if name == "demo":
        from .demo import DemoProvider
        return DemoProvider()
    if name == "anthropic":
        from .anthropic_client import AnthropicProvider
        return AnthropicProvider(
            settings.anthropic_api_key if settings else None,
            max_tokens=settings.anthropic_max_tokens if settings else None,
        )
    if name == "openai":
        from .openai_client import OpenAIProvider
        return OpenAIProvider(settings.openai_api_key if settings else None)
    if name == "google":
        from .google_client import GoogleProvider
        return GoogleProvider(
            settings.google_api_key if settings else None,
            image_model=settings.google_image_model if settings else "gemini-2.5-flash-image",
        )
    raise ValueError(f"알 수 없는 provider: {name!r} — 등록 provider: {PROVIDER_NAMES}")
