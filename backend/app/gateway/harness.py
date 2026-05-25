"""하네스 조립 추상 (6요소) + PassthroughHarness.

구체 스튜디오 하네스(브레인스토밍/디자인/리뷰 페르소나)는 M3~에서 서브클래스로 구현.
M1은 추상 + raw 증명용 Passthrough만 제공.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..providers.base import Message


@dataclass
class HarnessRequest:
    run_id: str
    studio: str            # brainstorming|design|review|deploy
    user_prompt: str
    provider: str          # anthropic|openai|google|fake
    is_marker: bool = False
    history: list[Message] = field(default_factory=list)
    answer: str | None = None      # AskUser 응답(다음 턴 재개)
    bypass: bool = False           # AskUser bypass(자동 기본값)


@dataclass
class AskPayload:
    trigger: str          # "a" | "b" | "c"
    question: str
    options: list[str]


@dataclass
class HarnessResult:
    text: str
    output_path: str
    meta: dict
    ask: AskPayload | None = None
    events: list[dict] = field(default_factory=list)


class Harness(ABC):
    """6요소: system_prompt·constraints·references·structured_output·critic·askuser_hook."""

    def system_prompt(self) -> str | None:
        return None

    def constraints(self) -> dict:
        return {}

    def references(self) -> list:
        return []

    def structured_output_schema(self) -> dict | None:
        return None

    def critic(self, draft: str) -> str:
        return draft

    def askuser_hook(self):
        return None

    def output_path(self, req: HarnessRequest) -> str:
        return f"/{req.run_id}/{req.studio}/output.md"

    @abstractmethod
    def handle_turn(self, req: HarnessRequest, *, provider, store) -> HarnessResult: ...

    def build_messages(self, req: HarnessRequest) -> tuple[str | None, list[Message]]:
        return None, [*req.history, Message("user", req.user_prompt)]


class PassthroughHarness(Harness):
    """요소 미적용 raw 경로 (무료 티어 / M1 증명용)."""

    def handle_turn(self, req: HarnessRequest, *, provider, store) -> HarnessResult:
        system, messages = self.build_messages(req)
        system = system or self.system_prompt()
        resp = provider.complete(messages, model=req.provider, system=system)
        text = self.critic(resp.text)
        source = "marker" if req.is_marker else "raw"
        meta = {"source": source, "provider": req.provider, "grounds": []}
        path = self.output_path(req)
        store.put(path, text, meta=meta, source=source, mime="text/markdown")
        return HarnessResult(text=text, output_path=path, meta=meta,
                             events=[{"type": "artifact", "path": path}])

    def output_path(self, req: HarnessRequest) -> str:
        return f"/{req.run_id}/{req.studio}/passthrough.md"
