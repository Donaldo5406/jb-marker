"""테스트/오프라인용 결정론적 provider."""
from __future__ import annotations

from .base import Message, Provider, ProviderResponse


class FakeProvider(Provider):
    name = "fake"

    def complete(self, messages, *, model, system=None, **kwargs) -> ProviderResponse:
        last = messages[-1].content if messages else ""
        prefix = f"[{system}] " if system else ""
        return ProviderResponse(text=f"{prefix}echo: {last}", model=model, raw=None)
