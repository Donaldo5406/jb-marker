"""CriticVerdict 봉투 + 하네스 critic 출력 래핑 (spec §6)."""
import json

from app.gateway.critic import CriticVerdict


def test_verdict_to_dict_omits_none_scores():
    assert CriticVerdict(passed=True).to_dict() == {"passed": True, "issues": []}
    d = CriticVerdict(passed=False, issues=["factsheet"], scores={"avg": 2.1}).to_dict()
    assert d == {"passed": False, "issues": ["factsheet"], "scores": {"avg": 2.1}}


def test_from_scores_wraps_design_raw_grading():
    # design raw 채점({scores, avg, pass}) → wire 봉투 변환 지점 단일화
    raw = {"scores": {"layout": 4, "contrast": 3}, "avg": 3.5, "pass": 1}
    v = CriticVerdict.from_scores(raw)
    assert v.passed is True and isinstance(v.passed, bool)
    assert v.to_dict() == {"passed": True, "issues": [],
                           "scores": {"scores": {"layout": 4, "contrast": 3}, "avg": 3.5}}


def test_brainstorming_critic_returns_verdict():
    from app.gateway.harness_brainstorming import BrainstormingHarness
    v = BrainstormingHarness().critic("---\ngoal: x\n---\n본문")
    assert isinstance(v, CriticVerdict) and v.passed is False
    assert "factsheet" in v.issues


# --- design confirm 게이트 봉투의 critic 모양 (wire 변화 지점, spec §6) ---
# 픽스처는 test_design_gate.py의 게이트 정지 시나리오를 미러.


def _store(tmp_path):
    from app.vfs.local import LocalVfsStore
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


def test_design_s1_gate_critic_is_verdict_envelope(tmp_path):
    # S1 정지: critic == {"passed","issues","scores"} — scores에 7항목 raw + avg
    from app.gateway.harness_design import DesignHarness
    from app.providers.fake import FakeProvider
    s = _store(tmp_path)
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(), provider=FakeProvider(), store=s)
    assert res.gate.step == "S1"
    c = res.gate.critic
    assert set(c) == {"passed", "issues", "scores"}
    assert isinstance(c["passed"], bool) and c["issues"] == []
    assert "avg" in c["scores"]
    assert set(c["scores"]["scores"]) == set(DesignHarness.RUBRIC)


def test_design_s2b_gate_critic_lists_ungrounded_issues(tmp_path):
    # S2b 정지(ungrounded 수치): issues=[수치 토큰], scores 키 없음
    from app.gateway.harness_design import DesignHarness
    from app.providers.fake import FakeProvider
    s = _store(tmp_path)
    s.put("/r1/design/_state.json", json.dumps(
        {"step": "S2b", "gate": None, "confirmed": {}, "bypass": {},
         "languages": ["ko"], "pending_ask": None}),
        source="marker", mime="application/json")
    s.put("/r1/design/rough/layout.spec.json", json.dumps({"copy": {"ko": {}}}),
          source="marker", mime="application/json")

    class UngroundedCopy(FakeProvider):
        def complete(self, messages, *, model=None, system=None, tools=None, **kw):
            from app.providers.base import ProviderResponse
            return ProviderResponse(text=json.dumps(
                {"copy": {"ko": {"headline": "연 9.9% 특별적금", "body": "", "cta": "가입"}}}),
                model=model)

    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(action="advance"), provider=UngroundedCopy(), store=s)
    assert res.gate.step == "S2b"
    c = res.gate.critic
    assert c["passed"] is False and c["issues"] == ["9.9%"]
    assert "scores" not in c
