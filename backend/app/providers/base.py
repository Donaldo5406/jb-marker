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


class Provider(ABC):
    name: str = "base"

    @abstractmethod
    def complete(self, messages: list[Message], *, model: str,
                 system: str | None = None,
                 tools: list[dict] | None = None, **kwargs) -> ProviderResponse: ...

    def generate_image(self, prompt: str, *, aspect: str = "1:1") -> bytes:
        """텍스트-free 비주얼 PNG 생성(이미지 액터). 미지원 provider는 NotImplementedError."""
        raise NotImplementedError(f"{self.name} provider는 이미지 생성을 지원하지 않습니다")

    def review_image(self, image_bytes: bytes, prompt: str, *,
                     mime: str = "image/png") -> "ProviderResponse":
        """이미지를 vision으로 분석해 JSON 결과 텍스트 반환(R1 비전 호출).

        미지원 provider는 NotImplementedError. 결정론 테스트는 ScriptedProvider 사용.
        """
        raise NotImplementedError(
            f"{self.name} provider는 vision 검수를 지원하지 않습니다")
