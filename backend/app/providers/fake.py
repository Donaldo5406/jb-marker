"""테스트/오프라인용 결정론적 provider."""
from __future__ import annotations

from .base import Message, Provider, ProviderResponse


class FakeProvider(Provider):
    name = "fake"

    def complete(self, messages: list[Message], *, model: str | None = None,
                 system: str | None = None, tools: list[dict] | None = None,
                 meta: dict | None = None, **kwargs) -> ProviderResponse:
        last = messages[-1].content if messages else ""
        prefix = f"[{system}] " if system else ""
        citations = []
        if tools:
            citations = [{"url": "https://example.com/fake-source",
                          "title": "참고자료(더미)", "snippet": f"'{last}' 관련 더미 검색 결과"}]
        return ProviderResponse(text=f"{prefix}echo: {last}", model=model, raw=None,
                                citations=citations)

    def generate_image(self, prompt: str, *, aspect: str = "1:1") -> bytes:
        # 의존 없는 최소 1x1 PNG(결정론적 더미 — 오프라인/테스트)
        import base64
        return base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
        )

    def generate_video(self, prompt: str, *, aspect: str = "9:16",
                       duration_sec: int = 15, fps: int = 30) -> bytes:
        # 의존 없는 최소 mp4 시그니처 더미(결정론적 — 오프라인/테스트)
        return b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"

    def review_image(self, image_bytes, prompt, *, mime="image/png") -> ProviderResponse:
        """결정론 스텁 — 거짓 finding 만들지 않음(spec §7.3 거짓 BLOCK/PASS 방지)."""
        return ProviderResponse(text='{"findings":[]}', model="fake")
