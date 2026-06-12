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


# ---- Task 2: 오케스트레이터 — 연쇄·done·게이트 정지 ----

def test_step_names_derives_pipeline_and_next_step():
    o = _orch([_Step("A"), _Step("B")])
    assert o.step_names == ("A", "B", "done")
    assert o.next_step("A") == "B"
    assert o.next_step("B") == "done"
    assert o.next_step("done") == "done"          # 종단 고정점(원본 next_step :36-39)


def test_duplicate_step_names_rejected():
    with pytest.raises(ValueError):
        _orch([_Step("A"), _Step("A")])


def test_done_step_name_rejected():
    with pytest.raises(ValueError):
        _orch([_Step("done")])


def test_step_names_frozen_at_init():
    a = _Step("A")
    o = _orch([a])
    a.name = "Z"                                  # 생성 후 변경은 무시(스냅샷)
    assert o.step_names == ("A", "done")
    assert o.next_step("A") == "done"


def test_ungated_steps_chain_to_done(tmp_path):
    s = _store(tmp_path)
    a, b = _Step("A"), _Step("B")
    o = _orch([a, b])
    state = _state("A")
    res = o.handle_turn(_ctx(s, state))
    assert a.runs == 1 and b.runs == 1            # 한 턴에 전 단계 연쇄
    assert res.text == "완료했습니다."
    assert res.output_path == "/r1/design/final.md"
    assert res.meta == {"source": "marker", "step": "done", "auto_advanced": []}
    assert res.gate is None
    assert [e["path"] for e in res.events] == ["/r1/design/A.txt", "/r1/design/B.txt"]
    assert state["step"] == "done" and state["gate"] is None
    assert state["confirmed"] == {"A": True, "B": True}
    st = json.loads(s.get("/r1/design/_state.json").content_text)
    assert st["step"] == "done" and st["version"] == 1        # 저장 콜백 + version 백필
    assert s.get_manifest("r1").step_status["design"] == "done"   # set_step_status(studio 주입)


def test_gated_step_stops_with_confirm_envelope(tmp_path):
    s = _store(tmp_path)
    a = _Step("A")
    g = _Step("G", gated=True,
              check=lambda ctx: GateCheck(passed=False,
                                          critic={"passed": False, "issues": ["x"]}))
    o = _orch([a, g])
    state = _state("A")
    res = o.handle_turn(_ctx(s, state))
    assert a.runs == 1 and g.runs == 1
    assert state["gate"] == "G" and state["step"] == "G"      # 정지(검증 실패여도 자문일 뿐)
    assert state["confirmed"] == {"A": True}
    assert res.gate is not None and res.gate.kind == "confirm"
    assert res.gate.step == "G"
    assert res.gate.actions == ["confirm", "regenerate"]
    assert res.gate.critic == {"passed": False, "issues": ["x"]}
    assert res.gate.auto_advanced is None         # [] → None(wire 생략, 원본 :241)
    assert res.meta["step"] == "G"
    assert res.text == "G 완료"                    # last 결과의 text 전달
    st = json.loads(s.get("/r1/design/_state.json").content_text)
    assert st["gate"] == "G"                      # 정지 시 저장(원본 :222)


def test_gated_step_pass_critic_still_stops(tmp_path):
    # 게이트 ON에서 critic은 자문 — pass여도 정지한다(원본 :219-225).
    s = _store(tmp_path)
    g = _Step("G", gated=True)                    # 기본 check = pass·critic None
    o = _orch([g])
    state = _state("G")
    res = o.handle_turn(_ctx(s, state))
    assert state["gate"] == "G"
    assert res.gate.kind == "confirm" and res.gate.critic is None
