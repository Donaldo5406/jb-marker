"""하네스 계약 추상 + PassthroughHarness.

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
    action: str | None = None      # design step 액션: advance|confirm|regenerate|chat|answer
    user_id: str = "demo"          # 게이트(entitlement) 평가 대상. 기본 demo(로컬-우선)
    bypass_map: dict | None = None  # design 단계별 게이트 OFF 맵(프론트 전체 전송)


@dataclass
class GateEnvelope:
    """HITL 게이트 표준 봉투 (spec §4.1) — 스튜디오 3종 신호의 단일 wire 형식.

    kind="ask"(brainstorming AskUser) / "confirm"(design step 게이트) /
    "status"(review 판정). actions = 지금 보낼 수 있는 action 어휘의 서버 선언.
    """
    kind: str                                # "ask" | "confirm" | "status"
    # kind="ask"
    trigger: str | None = None               # "a" | "b" | "c"
    question: str | None = None
    options: list[str] | None = None
    # kind="confirm"
    step: str | None = None                  # 정지한 step ("S1"...)
    critic: dict | None = None               # 게이트 사유(채점/ungrounded)
    auto_advanced: list[str] | None = None   # bypass 연쇄 자동 통과 단계
    # kind="status"
    status: str | None = None                # "PASS" | "WARN" | "BLOCKED"
    critical_count: int | None = None
    warning_count: int | None = None
    # 공통
    actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """wire 형태 — None 필드는 생략, kind·actions는 항상 포함."""
        out = {"kind": self.kind, "actions": list(self.actions)}
        for k in ("trigger", "question", "options", "step", "critic",
                  "auto_advanced", "status", "critical_count", "warning_count"):
            v = getattr(self, k)
            if v is not None:
                out[k] = v
        return out


@dataclass
class HarnessResult:
    text: str
    output_path: str
    meta: dict
    gate: "GateEnvelope | None" = None
    events: list[dict] = field(default_factory=list)


class Harness(ABC):
    """계약: handle_turn(필수) + output_path + (선택) system_prompt.

    종전 6요소 선언 중 프롬프트 요소(constraints·references·structured_output)는
    PromptSpec(gateway/prompt.py)의 필드로, critic 출력은 CriticVerdict(gateway/critic.py)로
    실체화 — 선언만 있고 구현 없던 메서드들은 제거.
    """

    def system_prompt(self) -> str | None:
        return None

    def output_path(self, req: HarnessRequest) -> str:
        return f"/{req.run_id}/{req.studio}/output.md"

    @abstractmethod
    def handle_turn(self, req: HarnessRequest, *, provider, store) -> HarnessResult: ...


class PassthroughHarness(Harness):
    """요소 미적용 raw 경로 (무료 티어 / M1 증명용)."""

    def build_messages(self, req: HarnessRequest) -> tuple[str | None, list[Message]]:
        return None, [*req.history, Message("user", req.user_prompt)]

    def handle_turn(self, req: HarnessRequest, *, provider, store) -> HarnessResult:
        system, messages = self.build_messages(req)
        system = system or self.system_prompt()
        resp = provider.complete(messages, system=system)
        text = resp.text
        source = "marker" if req.is_marker else "raw"
        meta = {"source": source, "provider": req.provider, "grounds": []}
        path = self.output_path(req)
        store.put(path, text, meta=meta, source=source, mime="text/markdown")
        return HarnessResult(text=text, output_path=path, meta=meta,
                             events=[{"type": "artifact", "path": path}])

    def output_path(self, req: HarnessRequest) -> str:
        # _ 접두 → 프론트 FileTree 숨김(스펙외 산출물 비가시화). 라운드트립은 보존.
        return f"/{req.run_id}/{req.studio}/_passthrough.md"
