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


# ---- Task 3: 게이트 재개 3분기 ----

def _gated_pipeline(tmp_path, check=None):
    """G(게이트)→B(비게이트) 파이프라인을 G 정지 상태로 만든다."""
    s = _store(tmp_path)
    g = _Step("G", gated=True, check=check)
    b = _Step("B")
    o = _orch([g, b])
    state = _state("G")
    o.handle_turn(_ctx(s, state))                 # → gate G 정지
    assert state["gate"] == "G"
    return s, g, b, o, state


def test_confirm_resumes_and_chains(tmp_path):
    s, g, b, o, state = _gated_pipeline(tmp_path)
    res = o.handle_turn(_ctx(s, state, _req(action="confirm")))
    assert state["confirmed"]["G"] is True
    assert g.runs == 1                            # 승인은 재실행 없음(원본 :168-172)
    assert b.runs == 1                            # 다음 step부터 연쇄
    assert res.meta["step"] == "done"             # B 비게이트 → done까지


def test_advance_behaves_like_confirm(tmp_path):
    s, g, b, o, state = _gated_pipeline(tmp_path)
    o.handle_turn(_ctx(s, state, _req(action="advance")))
    assert g.runs == 1 and b.runs == 1


def test_regenerate_reruns_and_keeps_gate(tmp_path):
    s, g, b, o, state = _gated_pipeline(tmp_path)
    res = o.handle_turn(_ctx(s, state, _req(action="regenerate")))
    assert g.runs == 2 and b.runs == 0            # 해당 step만 재생성(원본 :173-181)
    assert state["gate"] == "G" and state["step"] == "G"
    assert res.gate.kind == "confirm" and res.gate.step == "G"
    assert res.text == "G 완료"


def test_prompt_refinement_reruns_like_regenerate(tmp_path):
    s, g, b, o, state = _gated_pipeline(tmp_path)
    res = o.handle_turn(_ctx(s, state, _req(prompt="더 강렬하게")))
    assert g.runs == 2 and b.runs == 0            # user_prompt 정제도 재생성 경로
    assert state["gate"] == "G"
    assert res.gate.kind == "confirm"


def test_regenerate_reconsults_critic(tmp_path):
    calls = []

    def check(ctx):
        calls.append(1)
        return GateCheck(passed=False,
                         critic={"passed": False, "issues": [f"n{len(calls)}"]})

    s, g, b, o, state = _gated_pipeline(tmp_path, check=check)
    res = o.handle_turn(_ctx(s, state, _req(action="regenerate")))
    assert len(calls) == 2                        # 정지 1회 + 재생성 자문 1회
    assert res.gate.critic == {"passed": False, "issues": ["n2"]}


def test_empty_poll_reexposes_gate_without_rerun(tmp_path):
    s, g, b, o, state = _gated_pipeline(tmp_path)
    res = o.handle_turn(_ctx(s, state, _req()))
    assert g.runs == 1 and b.runs == 0            # 재실행 없음 = LLM 0회(원본 :182-185)
    assert res.gate.kind == "confirm" and res.gate.step == "G"
    assert res.text == "확정 대기 중입니다."
    assert res.output_path == "/r1/design/_state.json"
    assert res.meta == {"source": "marker", "step": "G"}
    assert res.events == []                       # 재실행 없음의 wire 증거
    assert res.gate.critic is None
    assert res.gate.auto_advanced is None


def test_confirm_on_last_step_goes_done(tmp_path):
    s = _store(tmp_path)
    g = _Step("G", gated=True)
    o = _orch([g])
    state = _state("G")
    o.handle_turn(_ctx(s, state))                 # → gate G 정지
    res = o.handle_turn(_ctx(s, state, _req(action="confirm")))
    assert g.runs == 1                            # 재실행 없음
    assert res.meta == {"source": "marker", "step": "done", "auto_advanced": []}
    assert state["gate"] is None and state["step"] == "done"
    assert s.get_manifest("r1").step_status["design"] == "done"


# ---- Task 4: bypass 연쇄·재생성 한도·cache 계약 (구현은 Task 2 — 이식 검증) ----

def test_bypass_map_merges_into_state(tmp_path):
    s = _store(tmp_path)
    g = _Step("G", gated=True)
    o = _orch([g])
    state = _state("G")
    res = o.handle_turn(_ctx(s, state, _req(bypass_map={"G": True})))
    assert state["bypass"] == {"G": True}         # req.bypass_map 병합(원본 :163-164)
    assert res.meta["step"] == "done"             # bypass+pass → 정지 없이 done
    assert res.meta["auto_advanced"] == ["G"]


def test_bypass_critic_fail_regenerates_once_then_warns(tmp_path):
    s = _store(tmp_path)
    g = _Step("G", gated=True, check=lambda ctx: GateCheck(passed=False))
    o = _orch([g])
    state = _state("G")
    state["bypass"] = {"G": True}
    res = o.handle_turn(_ctx(s, state))
    assert g.runs == 2                            # 1회 재생성 한도(원본 :210-212)
    assert res.meta["warnings"] == ["G"]          # 2차도 실패 → 경고 후 진행(:213-214)
    assert res.meta["auto_advanced"] == ["G"]
    assert res.meta["step"] == "done"
    assert state["confirmed"]["G"] is True


def test_bypass_critic_pass_skips_regeneration(tmp_path):
    s = _store(tmp_path)
    g = _Step("G", gated=True)                    # 기본 critic=pass
    o = _orch([g])
    state = _state("G")
    state["bypass"] = {"G": True}
    res = o.handle_turn(_ctx(s, state))
    assert g.runs == 1
    assert "warnings" not in res.meta


def test_gate_stop_carries_auto_advanced_and_warnings(tmp_path):
    # bypass된 G1(critic 2회 실패)을 지나 G2(bypass OFF) 정지 — 봉투에 이력 전달(원본 :223-225)
    s = _store(tmp_path)
    g1 = _Step("G1", gated=True, check=lambda ctx: GateCheck(passed=False))
    g2 = _Step("G2", gated=True)
    o = _orch([g1, g2])
    state = _state("G1")
    state["bypass"] = {"G1": True}
    res = o.handle_turn(_ctx(s, state))
    assert state["gate"] == "G2"
    assert res.gate.auto_advanced == ["G1"]
    assert res.meta["warnings"] == ["G1"]


def test_cache_shared_within_turn_and_overwritten_on_rerun(tmp_path):
    # cache 계약: run이 키를 '덮어쓰고' critic_gate가 읽는다 — 같은 턴 내
    # 1회 재생성에서 stale 채점 방지(spec §8). P2 S3 critic 단일화의 기반.
    class Caching(PipelineStep):
        name = "C"
        gated = True

        def __init__(self):
            self.runs = 0

        def run(self, ctx):
            self.runs += 1
            ctx.cache["score"] = self.runs        # 항상 덮어쓰기
            return HarnessResult(text="c", output_path=f"{ctx.base}/c.txt",
                                 meta={"source": "marker", "step": "C"})

        def critic_gate(self, ctx):
            return GateCheck(passed=ctx.cache["score"] >= 2,
                             critic={"seen": ctx.cache["score"]})

    s = _store(tmp_path)
    c = Caching()
    o = _orch([c])
    state = _state("C")
    state["bypass"] = {"C": True}
    res = o.handle_turn(_ctx(s, state))
    assert c.runs == 2                            # 1차 fail(score=1)→재생성→2차 pass(score=2)
    assert "warnings" not in res.meta             # 재생성 후 통과 = 신선한 값으로 판정


# ---- P2 Task 1: 하드닝 — 승인 어휘 상수화 + 알 수 없는 step 명시 에러 ----

def test_confirm_actions_single_source():
    # 체크리스트 ②: 승인 어휘는 모듈 상수 단일 출처(분기 인라인 튜플 금지)
    from app.gateway.pipeline import CONFIRM_ACTIONS, GATE_ACTIONS
    assert CONFIRM_ACTIONS == ("advance", "confirm")
    assert GATE_ACTIONS == ("confirm", "regenerate")


def test_unknown_step_in_chain_raises_explicit_error(tmp_path):
    # 체크리스트 ①: state["step"]가 미등록 이름이면 KeyError 대신 명시 에러
    s = _store(tmp_path)
    o = _orch([_Step("A")])
    state = _state("ZZZ")
    with pytest.raises(ValueError, match="알 수 없는 step"):
        o.handle_turn(_ctx(s, state))


def test_unknown_gate_step_on_regenerate_raises_explicit_error(tmp_path):
    # (b) 재생성 분기의 _by_name[gate]도 동일 하드닝
    s = _store(tmp_path)
    o = _orch([_Step("A")])
    state = _state("A")
    state["gate"] = "ZZZ"
    with pytest.raises(ValueError, match="알 수 없는 step"):
        o.handle_turn(_ctx(s, state, _req(action="regenerate")))


def test_unknown_gate_step_on_confirm_raises_explicit_error(tmp_path):
    # (a) 승인 분기 대칭화(P2 통합리뷰 이월): next_step의 미등록 gate도
    # tuple.index의 bare ValueError가 아닌 (b)·(c)와 동일 양식의 명시 에러
    s = _store(tmp_path)
    o = _orch([_Step("A")])
    state = _state("A")
    state["gate"] = "ZZZ"
    # next_step 메시지는 done 포함(고정점·적법 입력)이라는 비대칭의 절반까지 핀
    with pytest.raises(ValueError, match=r"알 수 없는 step 'ZZZ' — 등록 step: \('A', 'done'\)$"):
        o.handle_turn(_ctx(s, state, _req(action="confirm")))


def test_unknown_step_error_lists_registered_without_done(tmp_path):
    # _step 메시지의 '등록 step' 목록은 실제 등록 step만 — 예약어 done 비포함(P2 통합리뷰 이월)
    s = _store(tmp_path)
    o = _orch([_Step("A"), _Step("B")])
    with pytest.raises(ValueError, match=r"등록 step: \('A', 'B'\)$"):
        o.handle_turn(_ctx(s, _state("ZZZ")))
