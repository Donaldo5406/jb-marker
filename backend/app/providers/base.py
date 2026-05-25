"""Provider 추상 — 모든 AI 호출의 공통 표면 (marker_api.md §3-2)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
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


class Provider(ABC):
    name: str = "base"

    @abstractmethod
    def complete(self, messages: list[Message], *, model: str,
                 system: str | None = None, **kwargs) -> ProviderResponse: ...
