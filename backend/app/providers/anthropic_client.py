"""AnthropicProvider (live) — 키 필요. 테스트는 FakeProvider 사용."""
from __future__ import annotations

from .base import Message, Provider, ProviderResponse


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    def complete(self, messages, *, model, system=None, **kwargs) -> ProviderResponse:
        from anthropic import Anthropic
        client = Anthropic(api_key=self._api_key)
        resp = client.messages.create(
            model=model, max_tokens=kwargs.get("max_tokens", 2048),
            system=system or "",
            messages=[{"role": m.role, "content": m.content} for m in messages if m.role != "system"],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        return ProviderResponse(text=text, model=model, raw=resp)
