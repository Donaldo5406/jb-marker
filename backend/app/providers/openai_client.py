"""OpenAIProvider (live)."""
from __future__ import annotations

from .base import Message, Provider, ProviderResponse


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    def complete(self, messages, *, model, system=None, **kwargs) -> ProviderResponse:
        from openai import OpenAI
        client = OpenAI(api_key=self._api_key)
        msgs = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": m.role, "content": m.content} for m in messages]
        resp = client.chat.completions.create(model=model, messages=msgs)
        return ProviderResponse(text=resp.choices[0].message.content or "", model=model, raw=resp)
