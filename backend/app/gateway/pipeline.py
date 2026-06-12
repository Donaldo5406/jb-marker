"""범용 step-pipeline 골격 — StepContext·GateCheck·PipelineStep·PipelineOrchestrator (T3, spec §4.1).

DesignHarness.handle_turn(harness_design.py:161-243)의 제어 흐름을 design
비의존으로 일반화. 오케스트레이터는 design을 모른다 — studio명·done 텍스트·
산출 경로·저장은 주입. state 키(step·gate·confirmed·bypass)는 오케스트레이터
소유, 도메인 키(languages 등)는 하네스/단계 소유.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

from .harness import GateEnvelope, HarnessRequest, HarnessResult


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


DONE = "done"
GATE_ACTIONS = ("confirm", "regenerate")   # confirm 게이트 어휘(GateEnvelope.actions 서버 선언)


class PipelineOrchestrator:
    """단계 시퀀스를 받아 step-pipeline 제어 흐름을 실행 (이식 원본: harness_design.py:161-243).

    게이트 4분기 — (a) confirm/advance 승인 (b) regenerate/프롬프트 정제
    (b') 무내용 폴링 재노출 (c) 연쇄 루프(bypass→critic→1회 재생성→warnings→
    auto_advanced).
    """

    def __init__(self, steps, *, studio: str, done_text: str, done_output: str,
                 save_state: Callable[[Any, str, dict], None]) -> None:
        """steps: PipelineStep 시퀀스(순서=파이프라인). done_output: base-상대 경로.

        save_state(store, run_id, state) — 저장 규약은 하네스 소유(스튜디오별
        default가 다름)라 주입. studio는 set_step_status용 manifest 어휘.
        """
        self._steps = tuple(steps)
        self._by_name = {s.name: s for s in self._steps}
        if len(self._by_name) != len(self._steps):
            raise ValueError("step name 중복")
        if DONE in self._by_name:
            raise ValueError(f"step name {DONE!r}은 예약어")
        self._names = tuple(s.name for s in self._steps) + (DONE,)   # init 스냅샷(이후 name 변경 무시)
        self.studio = studio
        self._done_text = done_text
        self._done_output = done_output
        self._save_state = save_state

    @property
    def step_names(self) -> tuple[str, ...]:
        return self._names

    def next_step(self, step: str) -> str:
        """시퀀스에서 다음 단계. done은 고정점(원본 next_step :36-39)."""
        names = self.step_names
        idx = names.index(step)
        return names[idx + 1] if idx + 1 < len(names) else DONE

    def handle_turn(self, ctx: StepContext) -> HarnessResult:
        req, state = ctx.req, ctx.state
        if getattr(req, "bypass_map", None):
            state.setdefault("bypass", {}).update(req.bypass_map)
        action = getattr(req, "action", None)
        gate = state.get("gate")

        # (a) 게이트 정지 중 confirm/advance → 승인하고 다음으로 (원본 :168-172)
        if gate and action in ("advance", "confirm"):
            state["confirmed"][gate] = True
            state["gate"] = None
            state["step"] = self.next_step(gate)
        # (b) 게이트 정지 중 regenerate / 프롬프트 정제 → 해당 step 재생성, gate 유지 (원본 :173-181)
        elif gate and (action == "regenerate" or (req.user_prompt or "").strip()):
            step_obj = self._by_name[gate]
            result = step_obj.run(ctx)
            check = step_obj.critic_gate(ctx)
            state["gate"] = gate
            state["step"] = gate
            self._save_state(ctx.store, req.run_id, state)
            return self._gate_result(ctx, gate, result.events, last=result,
                                     critic=check.critic)
        # (b') 무내용 폴링 → 재생성 없이 현 게이트 재노출(LLM 호출 없음) (원본 :182-185)
        elif gate:
            self._save_state(ctx.store, req.run_id, state)
            return self._gate_result(ctx, gate, [])

        # (c) 현재 step부터 연쇄 루프 (원본 :187-228)
        step = state["step"]
        events: list = []
        regen: dict = {}
        warnings: list = []
        auto_advanced: list = []
        while True:
            if step == DONE:
                state["gate"] = None
                self._save_state(ctx.store, req.run_id, state)
                ctx.store.set_step_status(req.run_id, self.studio, "done")
                meta = {"source": "marker", "step": DONE,
                        "auto_advanced": auto_advanced}
                if warnings:
                    meta["warnings"] = warnings
                return HarnessResult(text=self._done_text,
                                     output_path=f"{ctx.base}/{self._done_output}",
                                     meta=meta, events=events)
            step_obj = self._by_name[step]
            result = step_obj.run(ctx)
            events += result.events
            if step_obj.gated:
                bypassed = bool(state.get("bypass", {}).get(step))
                check = step_obj.critic_gate(ctx)
                if bypassed:
                    if not check.passed and regen.get(step, 0) < 1:
                        regen[step] = 1
                        continue                   # 같은 step 1회 재생성
                    if not check.passed:
                        warnings.append(step)      # 2차도 실패 → 경고 후 진행
                    state["confirmed"][step] = True
                    auto_advanced.append(step)
                    step = state["step"] = self.next_step(step)
                    continue                       # 연쇄
                else:                              # 게이트 ON → 정지(check는 자문)
                    state["gate"] = step
                    state["step"] = step
                    self._save_state(ctx.store, req.run_id, state)
                    return self._gate_result(ctx, step, events, last=result,
                                             critic=check.critic,
                                             auto_advanced=auto_advanced,
                                             warnings=warnings)
            # 비게이트 → 통과 후 다음으로 체인
            state["confirmed"][step] = True
            step = state["step"] = self.next_step(step)

    def _gate_result(self, ctx: StepContext, gate: str, events: list, *,
                     last: HarnessResult | None = None, critic: dict | None = None,
                     auto_advanced: list | None = None,
                     warnings: list | None = None) -> HarnessResult:
        """게이트 정지 응답 조립 (이식 원본: _gate_result :230-243 — wire 동일)."""
        out = last.output_path if last is not None else f"{ctx.base}/_state.json"
        meta = dict(last.meta) if last is not None else {"source": "marker"}
        meta["step"] = gate
        if warnings:
            meta["warnings"] = warnings
        text = last.text if last is not None else "확정 대기 중입니다."
        return HarnessResult(text=text, output_path=out, meta=meta,
                             gate=GateEnvelope(kind="confirm", step=gate,
                                               critic=critic,
                                               auto_advanced=auto_advanced or None,
                                               actions=list(GATE_ACTIONS)),
                             events=events)
