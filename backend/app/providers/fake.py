"""테스트/오프라인용 결정론적 provider."""
from __future__ import annotations

from .base import Message, Provider, ProviderResponse


class FakeProvider(Provider):
    name = "fake"

    def complete(self, messages, *, model, system=None, tools=None, **kwargs) -> ProviderResponse:
        last = messages[-1].content if messages else ""
        prefix = f"[{system}] " if system else ""
        citations = []
        if tools:
            citations = [{"url": "https://example.com/fake-source",
                          "title": "참고자료(더미)", "snippet": f"'{last}' 관련 더미 검색 결과"}]
        return ProviderResponse(text=f"{prefix}echo: {last}", model=model, raw=None,
                                citations=citations)
