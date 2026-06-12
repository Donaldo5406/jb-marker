"""범용 step-pipeline 골격 — StepContext·GateCheck·PipelineStep·PipelineOrchestrator (T3, spec §4.1).

DesignHarness.handle_turn(harness_design.py:161-243)의 제어 흐름을 design
비의존으로 일반화. 오케스트레이터는 design을 모른다 — studio명·done 텍스트·
산출 경로·저장은 주입. state 키(step·gate·confirmed·bypass)는 오케스트레이터
소유, 도메인 키(languages 등)는 하네스/단계 소유.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .harness import HarnessRequest, HarnessResult


@dataclass
class StepContext:
    """단계가 받는 턴 스코프 입력 묶음.

    cache는 같은 턴 내 run→critic_gate 공유 채널 — run은 키를 '덮어쓴다'
    (append 금지: 같은 턴 내 1회 재생성 시 stale 값 방지, spec §8).
    """
    req: HarnessRequest
    provider: Any            # 텍스트 provider(매체 프로바이더는 단계 생성자 주입)
    store: Any
    state: dict
    base: str                # 예: /{run_id}/design
    cache: dict = field(default_factory=dict)


@dataclass
class GateCheck:
    """단계 품질 판정 — 구 _critic_gate 반환 {'passed','critic'}의 타입화."""
    passed: bool
    critic: dict | None = None   # CriticVerdict.to_dict() — GateEnvelope.critic에 실림


class PipelineStep(ABC):
    """파이프라인 1단계. name=meta·state 키의 단일 출처, gated=confirm 게이트 대상."""

    name: str
    gated: bool = False

    @abstractmethod
    def run(self, ctx: StepContext) -> HarnessResult: ...

    def critic_gate(self, ctx: StepContext) -> GateCheck:
        return GateCheck(passed=True)   # 기본 = critic 없음(항상 통과)


class PipelineOrchestrator:   # Task 2(P1-T2)에서 구현 — 임포트 표면 선점
    pass
