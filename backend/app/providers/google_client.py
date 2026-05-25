"""GoogleProvider (live) — google-genai SDK."""
from __future__ import annotations

from .base import Message, Provider, ProviderResponse


class GoogleProvider(Provider):
    name = "google"

    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    def complete(self, messages, *, model, system=None, **kwargs) -> ProviderResponse:
        from google import genai
        client = genai.Client(api_key=self._api_key)
        prompt = "\n".join(m.content for m in messages)
        resp = client.models.generate_content(model=model, contents=prompt)
        return ProviderResponse(text=getattr(resp, "text", ""), model=model, raw=resp)
