"""GoogleProvider (live) — google-genai SDK."""
from __future__ import annotations

from .base import Message, Provider, ProviderResponse


class GoogleProvider(Provider):
    name = "google"

    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    def complete(self, messages, *, model, system=None, tools=None, **kwargs) -> ProviderResponse:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=self._api_key)
        prompt = (f"{system}\n\n" if system else "") + "\n".join(m.content for m in messages)
        cfg = types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]) if tools else None
        resp = client.models.generate_content(model=model, contents=prompt, config=cfg)
        text = getattr(resp, "text", "") or ""
        citations = []
        try:
            chunks = resp.candidates[0].grounding_metadata.grounding_chunks or []
            for ch in chunks:
                w = getattr(ch, "web", None)
                if w:
                    citations.append({"url": getattr(w, "uri", None), "title": getattr(w, "title", None), "snippet": None})
        except Exception:
            pass
        return ProviderResponse(text=text, model=model, raw=resp, citations=citations)
