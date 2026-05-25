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
