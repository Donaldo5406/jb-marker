"""AnthropicProvider (live) — 키 필요. 테스트는 FakeProvider 사용."""
from __future__ import annotations

from .base import Message, Provider, ProviderResponse


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    def complete(self, messages, *, model, system=None, tools=None, **kwargs) -> ProviderResponse:
        from anthropic import Anthropic
        client = Anthropic(api_key=self._api_key)
        api_tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}] if tools else []
        resp = client.messages.create(
            model=model, max_tokens=kwargs.get("max_tokens", 2048),
            system=system or "",
            tools=api_tools,
            messages=[{"role": m.role, "content": m.content} for m in messages if m.role != "system"],
        )
        text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", None) == "text")
        citations = []
        for b in resp.content:
            for c in (getattr(b, "citations", None) or []):
                citations.append({"url": getattr(c, "url", None),
                                  "title": getattr(c, "title", None),
                                  "snippet": getattr(c, "cited_text", None)})
        usage = None
        u = getattr(resp, "usage", None)
        if u is not None:
            usage = {
                "input_tokens": int(getattr(u, "input_tokens", 0) or 0),
                "output_tokens": int(getattr(u, "output_tokens", 0) or 0),
            }
        return ProviderResponse(text=text, model=model, raw=resp, citations=citations, usage=usage)
