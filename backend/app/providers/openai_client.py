"""OpenAIProvider (live)."""
from __future__ import annotations

from .base import Message, Provider, ProviderResponse


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    def complete(self, messages: list[Message], *, model: str | None = None,
                 system: str | None = None, tools: list[dict] | None = None,
                 meta: dict | None = None, **kwargs) -> ProviderResponse:
        from openai import OpenAI
        client = OpenAI(api_key=self._api_key)
        msgs = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": m.role, "content": m.content} for m in messages]
        if tools:
            try:
                resp = client.chat.completions.create(model=model, messages=msgs, web_search_options={})
            except Exception:
                resp = client.chat.completions.create(model=model, messages=msgs)
        else:
            resp = client.chat.completions.create(model=model, messages=msgs)
        msg = resp.choices[0].message
        citations = []
        for ann in (getattr(msg, "annotations", None) or []):
            url = getattr(getattr(ann, "url_citation", None), "url", None)
            if url:
                citations.append({"url": url, "title": getattr(ann.url_citation, "title", None), "snippet": None})
        usage = None
        u = getattr(resp, "usage", None)
        if u is not None:
            usage = {
                "input_tokens": int(getattr(u, "prompt_tokens", 0) or 0),
                "output_tokens": int(getattr(u, "completion_tokens", 0) or 0),
            }
        return ProviderResponse(text=msg.content or "", model=model, raw=resp, citations=citations, usage=usage)
