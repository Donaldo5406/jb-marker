import json

from app.gateway.harness_design import DesignHarness, next_step, STEPS
from app.providers.fake import FakeProvider
from app.vfs.local import LocalVfsStore


def test_next_step_walks_pipeline():
    assert next_step("S0") == "S1"
    assert next_step("S1") == "S2a"
    assert next_step("S2a") == "S2b"
    assert next_step("S2b") == "S2c"
    assert next_step("S2c") == "S3"
    assert next_step("S3") == "done"
    assert next_step("done") == "done"   # 종단 고정점


def test_default_state_has_gate_none():
    s = LocalVfsStore(storage_dir="data/runs")
    h = DesignHarness(image_provider=FakeProvider())
    st = h._load_state(s, "no_such_run")
    assert st["gate"] is None
    assert st["step"] == "S0"


def _store(tmp_path):
    s = LocalVfsStore(storage_dir=str(tmp_path))
    s.create_run("r1", languages=["ko"])
    s.put("/r1/brainstorming/plan.md",
          "---\ncreative_direction:\n  palette: [\"#0A84FF\"]\n  font: Inter\n  aspect: \"1:1\"\n"
          "factsheet:\n  rate: \"연 3.5%\"\n"
          "material_matrix: [{channel: instagram, lang: ko}]\nlanguages: [ko]\n---\n본문",
          source="marker", mime="text/markdown")
    return s


def _req(action="advance", prompt=""):
    from app.gateway.harness import HarnessRequest
    return HarnessRequest(run_id="r1", studio="design", user_prompt=prompt,
                          provider="fake", is_marker=True, action=action)


def test_first_turn_chains_s0_into_s1_then_gates(tmp_path):
    # S0 비게이트 → S1 생성 후 gate-ON 정지(bypass 없음)
    s = _store(tmp_path)
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(), provider=FakeProvider(), store=s)
    st = json.loads(s.get("/r1/design/_state.json").content_text)
    assert st["step"] == "S1" and st["gate"] == "S1"     # S1에서 정지
    assert st["confirmed"].get("S0") is True             # S0는 통과
    assert res.meta["step"] == "S1"
    assert s.get("/r1/design/design-system/tokens.json") is not None   # S0 산출
    assert s.get("/r1/design/rough/layout.spec.json") is not None      # S1 산출


def test_confirm_advances_and_generates_next_gate(tmp_path):
    s = _store(tmp_path)
    h = DesignHarness(image_provider=FakeProvider())
    h.handle_turn(_req(), provider=FakeProvider(), store=s)            # → gate S1
    res = h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)  # confirm S1 → gate S2a
    st = json.loads(s.get("/r1/design/_state.json").content_text)
    assert st["confirmed"]["S1"] is True
    assert st["step"] == "S2a" and st["gate"] == "S2a"
    assert s.list("/r1/design/design-system/components/visual")        # S2a 산출 존재


def test_walk_all_gates_to_done(tmp_path):
    # gate-ON 기본: 매 advance가 한 게이트씩 전진, 6번이면 done
    s = _store(tmp_path)
    h = DesignHarness(image_provider=FakeProvider())
    for _ in range(6):
        h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)
    st = json.loads(s.get("/r1/design/_state.json").content_text)
    assert st["step"] == "done" and st["gate"] is None
    assert s.get_manifest("r1").step_status["design"] == "done"


def _state(s, step, bypass):
    s.put("/r1/design/_state.json", json.dumps(
        {"step": step, "gate": None, "confirmed": {}, "bypass": bypass,
         "languages": ["ko"], "pending_ask": None}),
        source="marker", mime="application/json")


def test_bypass_chains_through_to_next_gate(tmp_path):
    # S1·S2a bypass, S2b 게이트 ON → 한 턴에 S1→S2a→S2b 정지
    s = _store(tmp_path)
    s.put("/r1/design/rough/layout.spec.json",
          json.dumps({"visual_concept": "c", "aspect": "1:1", "copy": {"ko": {}}}),
          source="marker", mime="application/json")
    _state(s, "S1", {"S1": True, "S2a": True})
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)
    st = json.loads(s.get("/r1/design/_state.json").content_text)
    assert st["step"] == "S2b" and st["gate"] == "S2b"
    assert st["confirmed"]["S1"] and st["confirmed"]["S2a"]
    assert res.gate.auto_advanced == ["S1", "S2a"]


def test_bypass_full_chain_to_done(tmp_path):
    s = _store(tmp_path)
    _state(s, "S1", {k: True for k in ("S1", "S2a", "S2b", "S2c", "S3")})
    s.put("/r1/design/rough/layout.spec.json", json.dumps({"copy": {"ko": {}}}),
          source="marker", mime="application/json")
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)
    assert json.loads(s.get("/r1/design/_state.json").content_text)["step"] == "done"
    assert s.get_manifest("r1").step_status["design"] == "done"
    assert res.meta["step"] == "done"


def test_bypass_critic_fail_regenerates_once(tmp_path):
    # S1 bypass + critic fail 2회 → provider 2회 호출(1회 재생성), warning 후 진행
    s = _store(tmp_path)
    _state(s, "S1", {"S1": True})
    calls = {"n": 0}

    class FailCritic(FakeProvider):
        def complete(self, messages, *, model, system=None, tools=None, **kw):
            from app.providers.base import ProviderResponse
            sysl = system or ""
            if "자기-크리틱" in sysl:                       # critic 호출
                return ProviderResponse(text=json.dumps(
                    {"scores": {"hierarchy": 1, "grid": 1, "whitespace": 1, "cta": 1,
                                "compliance": 1, "copy_visual": 1, "brand": 1}}), model=model)
            calls["n"] += 1                                # S1 생성 호출
            return ProviderResponse(text=json.dumps(
                {"reply": "x", "layout_spec": {"visual_concept": "c"}, "ready": True}), model=model)

    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(action="advance"), provider=FailCritic(), store=s)
    assert calls["n"] == 2                                  # 1회 자동 재생성
    st = json.loads(s.get("/r1/design/_state.json").content_text)
    assert st["confirmed"]["S1"] is True                    # 2차도 실패지만 진행
    assert res.meta.get("warnings")                         # warning 부착


def test_bypass_s2b_grounding_triggers_regeneration(tmp_path):
    # S2b bypass + ungrounded 카피 → 1회 재생성(생성 provider 2회 호출)
    s = _store(tmp_path)
    _state(s, "S2b", {"S2b": True})
    s.put("/r1/design/rough/layout.spec.json", json.dumps({"copy": {"ko": {}}}),
          source="marker", mime="application/json")
    s.put("/r1/brainstorming/plan.md",
          "---\nfactsheet:\n  rate: \"연 3.5%\"\n---\n본문",
          source="marker", mime="text/markdown")
    calls = {"n": 0}

    class UngroundedCopy(FakeProvider):
        def complete(self, messages, *, model, system=None, tools=None, **kw):
            from app.providers.base import ProviderResponse
            calls["n"] += 1
            return ProviderResponse(text=json.dumps(
                {"copy": {"ko": {"headline": "연 9.9% 특별적금", "body": "", "cta": "가입"}}}),
                model=model)

    h = DesignHarness(image_provider=FakeProvider())
    h.handle_turn(_req(action="advance"), provider=UngroundedCopy(), store=s)
    assert calls["n"] == 2                                  # grounding fail → 1회 재생성


def test_regenerate_at_gate_reruns_same_step(tmp_path):
    s = _store(tmp_path)
    s.put("/r1/design/_state.json", json.dumps(
        {"step": "S1", "gate": "S1", "confirmed": {"S0": True}, "bypass": {},
         "languages": ["ko"], "pending_ask": None}),
        source="marker", mime="application/json")
    s.put("/r1/design/rough/layout.spec.json", json.dumps({"visual_concept": "old"}),
          source="marker", mime="application/json")
    h = DesignHarness(image_provider=FakeProvider())

    class SpecProvider(FakeProvider):
        def complete(self, messages, *, model, system=None, tools=None, **kw):
            from app.providers.base import ProviderResponse
            return ProviderResponse(text=json.dumps(
                {"reply": "재생성", "layout_spec": {"visual_concept": "새 컨셉"}, "ready": True}),
                model=model)

    res = h.handle_turn(_req(action="regenerate"), provider=SpecProvider(), store=s)
    spec = json.loads(s.get("/r1/design/rough/layout.spec.json").content_text)
    assert spec["visual_concept"] == "새 컨셉"             # S1 재생성
    st = json.loads(s.get("/r1/design/_state.json").content_text)
    assert st["step"] == "S1" and st["gate"] == "S1"      # 정지 유지
    assert res.gate.step == "S1"


def test_empty_poll_at_gate_does_not_regenerate(tmp_path):
    s = _store(tmp_path)
    s.put("/r1/design/_state.json", json.dumps(
        {"step": "S1", "gate": "S1", "confirmed": {"S0": True}, "bypass": {},
         "languages": ["ko"], "pending_ask": None}),
        source="marker", mime="application/json")
    s.put("/r1/design/rough/layout.spec.json", json.dumps({"visual_concept": "keep"}),
          source="marker", mime="application/json")
    calls = {"n": 0}

    class Counting(FakeProvider):
        def complete(self, *a, **k):
            calls["n"] += 1
            return super().complete(*a, **k)

    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(action=None, prompt=""), provider=Counting(), store=s)
    assert calls["n"] == 0                                 # 재생성 없음
    spec = json.loads(s.get("/r1/design/rough/layout.spec.json").content_text)
    assert spec["visual_concept"] == "keep"               # 보존
    assert res.gate.step == "S1"


def test_gate_meta_critic_shape_and_no_premature_done(tmp_path):
    s = _store(tmp_path)
    h = DesignHarness(image_provider=FakeProvider())
    # S0→S1 게이트: S1은 CRITIC_STEP → gate.critic에 판정 dict
    res = h.handle_turn(_req(), provider=FakeProvider(), store=s)
    assert res.gate.step == "S1"
    assert res.gate.critic is not None
    assert "pass" in res.gate.critic
    # confirm S1 → S2a 게이트: S2a는 critic 단계 아님 → gate.critic None
    res = h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)
    assert res.gate.step == "S2a"
    assert res.gate.critic is None
    # S2a→S2b→S2c→S3 게이트까지 전진
    for _ in range(3):
        res = h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)
    assert res.gate.step == "S3"
    # S3 게이트 정지 중에는 매니페스트가 done이면 안 됨(조기 done 금지)
    assert s.get_manifest("r1").step_status.get("design") != "done"
    # confirm S3 → done. 이제서야 매니페스트 done
    res = h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)
    assert res.meta["step"] == "done"
    assert s.get_manifest("r1").step_status["design"] == "done"
