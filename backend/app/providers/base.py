"""Provider 추상 — 모든 AI 호출의 공통 표면 (marker_api.md §3-2)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    role: str   # "user" | "assistant" | "system"
    content: str


@dataclass
class ProviderResponse:
    text: str
    model: str
    raw: Any = None
    citations: list[dict] = field(default_factory=list)   # [{"url","title","snippet"}]
    # 토큰 사용량 — SDK 응답에서 추출. None=알 수 없음(Fake/오프라인 stub).
    # {"input_tokens": int, "output_tokens": int}
    usage: dict | None = None


class Provider(ABC):
    name: str = "base"

    @abstractmethod
    def complete(self, messages: list[Message], *, model: str | None = None,
                 system: str | None = None,
                 tools: list[dict] | None = None,
                 meta: dict | None = None, **kwargs) -> ProviderResponse:
        """공통 completion 표면.

        meta: 하네스 명시 신호 {studio, step} — DemoProvider만 소비(T7), 다른 구현체는 무시.
        model: None이면 호출자가 모델 미지정 — 프로덕션은 ModelBoundProvider(providers/wrappers.py)가 주입.
        """
        ...

    def generate_image(self, prompt: str, *, aspect: str = "1:1",
                       image: bytes | None = None,
                       image_size: str | None = None) -> bytes:
        """텍스트 포함 풀 포스터 PNG 생성(이미지 액터). image 주어지면 image-to-image 편집.
        미지원 provider는 NotImplementedError."""
        raise NotImplementedError(f"{self.name} provider는 이미지 생성을 지원하지 않습니다")

    def generate_video(self, prompt: str, *, aspect: str = "9:16",
                       duration_sec: int = 15, fps: int = 30) -> bytes:
        """텍스트-free 배경 footage(mp4 bytes) 생성(영상 액터). 미지원 provider는 NotImplementedError."""
        raise NotImplementedError(f"{self.name} provider는 영상 생성을 지원하지 않습니다")

    def review_image(self, image_bytes: bytes, prompt: str, *,
                     mime: str = "image/png") -> "ProviderResponse":
        """이미지를 vision으로 분석해 JSON 결과 텍스트 반환(R1 비전 호출).

        미지원 provider는 NotImplementedError. 결정론 테스트는 ScriptedProvider 사용.
        """
        raise NotImplementedError(
            f"{self.name} provider는 vision 검수를 지원하지 않습니다")
