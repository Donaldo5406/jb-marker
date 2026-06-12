"""gateway/pipeline.py 골격 단위 테스트 (T3 P1, spec §7-1).

전부 design 비의존 가짜 단계로 검증 — 골격 재사용성(영상 장착 가능성)의 실증.
studio 문자열 "design"은 manifest 어휘(set_step_status가 STUDIOS 검증)일 뿐
design 모듈 임포트는 없다.
"""
import json

import pytest

from app.gateway.harness import HarnessRequest, HarnessResult
from app.gateway.pipeline import (
    GateCheck,
    PipelineOrchestrator,
    PipelineStep,
    StepContext,
)
from app.gateway.state import save_state
from app.vfs.local import LocalVfsStore


class _Step(PipelineStep):
    """기록형 가짜 단계. check: None=기본(항상 pass) | Callable[[ctx], GateCheck]."""

    def __init__(self, name, *, gated=False, check=None):
        self.name = name
        self.gated = gated
        self._check = check
        self.runs = 0

    def run(self, ctx):
        self.runs += 1
        path = f"{ctx.base}/{self.name}.txt"
        ctx.store.put(path, f"{self.name} v{self.runs}", source="marker",
                      mime="text/plain")
        return HarnessResult(text=f"{self.name} 완료", output_path=path,
                             meta={"source": "marker", "step": self.name},
                             events=[{"type": "artifact", "path": path}])

    def critic_gate(self, ctx):
        if self._check is None:
            return super().critic_gate(ctx)
        return self._check(ctx)


def _store(tmp_path):
    s = LocalVfsStore(storage_dir=str(tmp_path))
    s.create_run("r1", languages=["ko"])
    return s


def _req(action=None, prompt="", bypass_map=None):
    return HarnessRequest(run_id="r1", studio="design", user_prompt=prompt,
                          provider="fake", is_marker=True, action=action,
                          bypass_map=bypass_map)


def _orch(steps):
    return PipelineOrchestrator(
        steps, studio="design", done_text="완료했습니다.", done_output="final.md",
        save_state=lambda store, run_id, st: save_state(store, run_id, "design", st))


def _state(step="A"):
    """골격 state 계약: step 필수 + gate/confirmed/bypass — 하네스 _load_state default가 보장."""
    return {"step": step, "gate": None, "confirmed": {}, "bypass": {}}


def _ctx(store, state, req=None):
    r = req or _req()
    return StepContext(req=r, provider=None, store=store, state=state,
                       base=f"/{r.run_id}/design")


# ---- Task 1: 타입 3종 ----

def test_gatecheck_defaults():
    c = GateCheck(passed=True)
    assert c.passed is True and c.critic is None


def test_pipelinestep_default_critic_gate_passes():
    class Plain(PipelineStep):
        name = "X"

        def run(self, ctx):
            return HarnessResult(text="", output_path="", meta={})

    s = Plain()
    assert s.gated is False                       # 클래스 기본값
    chk = s.critic_gate(None)
    assert isinstance(chk, GateCheck)
    assert chk.passed is True and chk.critic is None


def test_stepcontext_cache_is_per_instance():
    a = StepContext(req=None, provider=None, store=None, state={}, base="/r1/design")
    b = StepContext(req=None, provider=None, store=None, state={}, base="/r1/design")
    a.cache["k"] = 1
    assert b.cache == {}                          # default_factory 독립성
