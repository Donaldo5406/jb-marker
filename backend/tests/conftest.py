from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.providers.base import Message, Provider, ProviderResponse
from app.server import create_app


@pytest.fixture()
def client():
    return TestClient(create_app())


class ScriptedProvider(Provider):
    """결정론 테스트용 — complete/review_image 호출에 미리 큐잉된 응답을 pop.

    사용:
        sp = ScriptedProvider(complete_responses=[
            ProviderResponse(text='{"findings":[...]}', model="x"),
            ...
        ])
    """
    name = "scripted"

    def __init__(self, *, complete_responses: list[ProviderResponse] | None = None,
                 review_image_responses: list[ProviderResponse] | None = None,
                 complete_raises: Exception | None = None,
                 review_image_raises: Exception | None = None) -> None:
        self._complete_q = list(complete_responses or [])
        self._review_q = list(review_image_responses or [])
        self._complete_raises = complete_raises
        self._review_raises = review_image_raises
        self.calls_complete: list[dict] = []
        self.calls_review_image: list[dict] = []

    def complete(self, messages, *, model=None, system=None, tools=None, **kw):
        self.calls_complete.append({"messages": messages, "model": model,
                                    "system": system, "tools": tools, "kw": kw})
        if self._complete_raises is not None:
            raise self._complete_raises
        if not self._complete_q:
            return ProviderResponse(text="", model=model)
        return self._complete_q.pop(0)

    def review_image(self, image_bytes, prompt, *, mime="image/png"):
        self.calls_review_image.append({"bytes_len": len(image_bytes),
                                        "prompt": prompt, "mime": mime})
        if self._review_raises is not None:
            raise self._review_raises
        if not self._review_q:
            return ProviderResponse(text="", model="scripted")
        return self._review_q.pop(0)


@pytest.fixture
def make_scripted():
    """ScriptedProvider 인스턴스 빌더."""
    return ScriptedProvider
