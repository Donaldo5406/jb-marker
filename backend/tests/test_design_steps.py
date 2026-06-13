"""design/steps.py — 단계 선언·유도 상수·S3 critic 캐시 계약 (T3 P2, spec §7-2/§5-②)."""
import json

from app.gateway.design.steps import (
    CRITIC_STEPS,
    GATED_STEPS,
    S3_CRITIC_CACHE,
    STEP_CLASSES,
    STEPS,
    S1Rough,
    S3Final,
)
from app.gateway.harness import HarnessRequest
from app.gateway.pipeline import StepContext
from app.providers.fake import FakeProvider
from app.vfs.local import LocalVfsStore


def _store(tmp_path):
    s = LocalVfsStore(storage_dir=str(tmp_path))
    s.create_run("r1", languages=["ko"])
    s.put("/r1/design/rough/layout.spec.json",
          json.dumps({"copy": {"ko": {"headline": "든든한 적금"}}}),
          source="marker", mime="application/json")
    return s


class _CountingCritic(FakeProvider):
    """자기-크리틱 system 프롬프트 호출만 계수하고 FakeProvider에 위임."""

    def __init__(self):
        self.critic_calls = 0

    def complete(self, messages, *, model=None, system=None, tools=None, **kw):
        if "자기-크리틱" in (system or ""):
            self.critic_calls += 1
        return super().complete(messages, model=model, system=system,
                                tools=tools, **kw)


def _ctx(store, provider):
    req = HarnessRequest(run_id="r1", studio="design", user_prompt="",
                         provider="fake", is_marker=True, action="advance")
    return StepContext(req=req, provider=provider, store=store,
                       state={"step": "S3", "gate": None, "confirmed": {},
                              "bypass": {}, "languages": ["ko"]},
                       base="/r1/design")


def test_pipeline_order_copy_before_visual():
    """베이크는 grounded 카피를 입력받아야 하므로 S2b가 S2a보다 먼저."""
    from app.gateway.design.steps import STEPS, STEP_CLASSES
    names = [c.name for c in STEP_CLASSES]
    assert names.index("S2b") < names.index("S2a")
    assert STEPS.index("S2b") < STEPS.index("S2a")
    from app.gateway.harness_design import next_step
    assert next_step("S1") == "S2b"
    assert next_step("S2b") == "S2a"
    assert next_step("S2a") == "S2c"


def test_step_declarations_derive_constants():
    # 선언↔유도 동기(spec §7-2): 수기 튜플과 step 객체의 이름 불일치 원천 차단(체크리스트 ⑪)
    assert STEPS == tuple(c.name for c in STEP_CLASSES) + ("done",)
    # Task 3 재편: 카피(S2b)가 비주얼(S2a) 앞 — grounded 카피를 베이크 입력으로
    assert STEPS == ("S0", "S1", "S2b", "S2a", "S2c", "S3", "done")
    assert GATED_STEPS == tuple(c.name for c in STEP_CLASSES if c.gated)
    assert GATED_STEPS == ("S1", "S2b", "S2a", "S2c", "S3")
    assert CRITIC_STEPS == ("S1", "S3")
    assert set(CRITIC_STEPS) <= set(GATED_STEPS)


def test_s3_run_records_cache_and_critic_gate_reuses_it(tmp_path):
    # T1 백로그 ②: S3 채점은 턴당 1회 — run이 cache에 무조건부 기록(체크리스트 ④),
    # critic_gate는 LLM 재호출 없이 같은 채점을 재사용.
    s = _store(tmp_path)
    p = _CountingCritic()
    ctx = _ctx(s, p)
    step = S3Final()
    res = step.run(ctx)
    assert p.critic_calls == 1
    assert S3_CRITIC_CACHE in ctx.cache
    assert res.meta["critic"]["passed"] in (True, False)   # meta.critic 보존(체크리스트 ⑤)
    check = step.critic_gate(ctx)
    assert p.critic_calls == 1                              # 재호출 없음 — cache 재사용
    assert check.critic is not None
    assert check.critic["passed"] == res.meta["critic"]["passed"]   # 같은 채점에서 유래


def test_s1_critic_gate_scores_fresh_every_time(tmp_path):
    # S1은 비캐시 — bypass 1회 재생성 후 '신선한' 채점이 필요(현행 동작 보존).
    s = _store(tmp_path)
    p = _CountingCritic()
    ctx = _ctx(s, p)
    step = S1Rough()
    step.critic_gate(ctx)
    step.critic_gate(ctx)
    assert p.critic_calls == 2


def test_harness_reexports_are_derived_and_orchestrator_synced():
    # 체크리스트 ⑪: harness_design의 STEPS/GATED_STEPS/CRITIC_STEPS는 step 선언 유도값의
    # re-export이고, per-인스턴스 오케스트레이터의 step_names와도 일치해야 한다.
    import app.gateway.harness_design as hd
    assert hd.STEPS is STEPS
    assert hd.GATED_STEPS is GATED_STEPS
    assert hd.CRITIC_STEPS is CRITIC_STEPS
    from app.gateway.harness_design import DesignHarness
    h = DesignHarness(image_provider=FakeProvider())
    assert h._orch.step_names == STEPS          # 인스턴스 조립 누락 방지(동기 가드)
    assert h._orch.studio == "design"
