import json

from app.providers.base import ProviderResponse


class StubProvider:
    """미리 정한 JSON 텍스트를 순서대로 반환(LLM 대체)."""
    def __init__(self, responses): self._r = list(responses); self.calls = []
    def complete(self, messages, *, model, system=None, tools=None, **kw):
        self.calls.append({"system": system, "tools": tools, "messages": messages})
        r = self._r.pop(0)
        return ProviderResponse(text=r["text"], model=model, citations=r.get("citations", []))


def _store():
    from app.vfs.local import LocalVfsStore
    s = LocalVfsStore(); s.create_run("rb"); return s


def test_critic_reports_missing_plan_fields():
    from app.gateway.harness_brainstorming import BrainstormingHarness
    h = BrainstormingHarness()
    md = "---\ncreative_direction: x\nlanguages: [ko]\n---\n본문"
    missing = h.critic(md)
    assert "factsheet" in missing and "slots" in missing
    assert "creative_direction" not in missing


def test_critic_empty_when_all_present():
    from app.gateway.harness_brainstorming import BrainstormingHarness, REQUIRED_PLAN_FIELDS
    h = BrainstormingHarness()
    fm = "\n".join(f"{k}: v" for k in REQUIRED_PLAN_FIELDS)
    assert h.critic(f"---\n{fm}\n---\nbody") == []


def test_state_roundtrip_default_stage_a():
    from app.gateway.harness_brainstorming import BrainstormingHarness
    h = BrainstormingHarness(); s = _store()
    st = h._load_state(s, "rb")
    assert st["stage"] == "A" and st["spec_locked"] is False
    st["stage"] = "B"; h._save_state(s, "rb", st)
    assert h._load_state(s, "rb")["stage"] == "B"


def test_stage_a_writes_spec_and_research_and_returns_reply():
    from app.gateway.harness_brainstorming import BrainstormingHarness
    from app.gateway.harness import HarnessRequest
    h = BrainstormingHarness(); s = _store()
    stub = StubProvider([{
        "text": json.dumps({"reply": "주력 채널은 무엇인가요?",
                            "document": "---\ngoal: 적금 캠페인\n---\n# 기획",
                            "ask": {"trigger": "a", "question": "주력 채널?", "options": ["카톡", "이메일"]},
                            "ready": False}),
        "citations": [{"url": "https://x.com", "title": "금리표", "snippet": "연 3.5%"}],
    }])
    req = HarnessRequest(run_id="rb", studio="brainstorming", user_prompt="30대 적금 캠페인", provider="fake", is_marker=True)
    res = h.handle_turn(req, provider=stub, store=s)
    assert res.text == "주력 채널은 무엇인가요?"
    assert res.ask is not None and res.ask.trigger == "a"
    assert s.get("/rb/brainstorming/spec.md").content_text.startswith("---")
    research = s.list("/rb/brainstorming/assets/research")
    assert len(research) >= 1 and research[0].meta.get("source_url") == "https://x.com"
    assert len(h._load_messages(s, "rb")) == 2  # user + assistant
    assert stub.calls[0]["tools"] is not None


def test_stage_a_ready_proposes_b_when_not_bypass():
    from app.gateway.harness_brainstorming import BrainstormingHarness
    from app.gateway.harness import HarnessRequest
    h = BrainstormingHarness(); s = _store()
    stub = StubProvider([{"text": json.dumps(
        {"reply": "정리했습니다.", "document": "---\ngoal: x\n---\n본문", "ask": None, "ready": True})}])
    req = HarnessRequest(run_id="rb", studio="brainstorming", user_prompt="좋아 정리해줘", provider="fake", is_marker=True)
    res = h.handle_turn(req, provider=stub, store=s)
    assert res.ask is not None and res.ask.trigger == "b"
    assert h._load_state(s, "rb")["stage"] == "A"  # 아직 전환 전(사용자 확정 대기)


def _seed_stage_b(h, s):
    st = h._load_state(s, "rb"); st["stage"] = "B"; st["spec_locked"] = True
    h._save_state(s, "rb", st)
    s.put("/rb/brainstorming/spec.md", "---\ngoal: 적금\n---\n본문", source="marker", mime="text/markdown")


def test_b_accepts_spec_lock_from_pending_b_then_runs():
    from app.gateway.harness_brainstorming import BrainstormingHarness, REQUIRED_PLAN_FIELDS
    from app.gateway.harness import HarnessRequest
    h = BrainstormingHarness(); s = _store()
    st = h._load_state(s, "rb")
    st["pending_ask"] = {"trigger": "b", "question": "?", "options": ["예", "아니오"]}
    h._save_state(s, "rb", st)
    s.put("/rb/brainstorming/spec.md", "---\ngoal: x\n---\nb", source="marker", mime="text/markdown")
    full = "---\n" + "\n".join(f"{k}: v" for k in REQUIRED_PLAN_FIELDS) + "\n---\n계획"
    stub = StubProvider([{"text": json.dumps({"reply": "계획 초안입니다.", "document": full, "ask": None, "ready": True})}])
    req = HarnessRequest(run_id="rb", studio="brainstorming", user_prompt="예", provider="fake", is_marker=True, answer="예, plan으로")
    res = h.handle_turn(req, provider=stub, store=s)
    assert s.get("/rb/brainstorming/plan.md") is not None
    assert h._load_state(s, "rb")["stage"] == "B"   # plan 확정 전(다음 b 대기)
    assert res.ask is not None and res.ask.trigger == "b"  # plan lock 확인 요청


def test_b_missing_contract_field_asks_c():
    from app.gateway.harness_brainstorming import BrainstormingHarness
    from app.gateway.harness import HarnessRequest
    h = BrainstormingHarness(); s = _store(); _seed_stage_b(h, s)
    partial = "---\ncreative_direction: x\nlanguages: [ko]\n---\n계획"
    stub = StubProvider([{"text": json.dumps({"reply": "초안", "document": partial, "ask": None, "ready": True})}])
    req = HarnessRequest(run_id="rb", studio="brainstorming", user_prompt="계획 짜줘", provider="fake", is_marker=True)
    res = h.handle_turn(req, provider=stub, store=s)
    assert res.ask is not None and res.ask.trigger == "c"
    assert "factsheet" in res.ask.question  # 누락 필드 안내


def test_b_plan_lock_sets_step_done():
    from app.gateway.harness_brainstorming import BrainstormingHarness, REQUIRED_PLAN_FIELDS
    from app.gateway.harness import HarnessRequest
    h = BrainstormingHarness(); s = _store()
    st = h._load_state(s, "rb"); st["stage"] = "B"; st["spec_locked"] = True
    st["pending_ask"] = {"trigger": "b", "question": "plan 확정?", "options": ["예", "아니오"]}
    h._save_state(s, "rb", st)
    full_fm = "\n".join(f"{k}: v" for k in REQUIRED_PLAN_FIELDS)
    s.put("/rb/brainstorming/plan.md", f"---\n{full_fm}\n---\n계획", source="marker", mime="text/markdown")
    req = HarnessRequest(run_id="rb", studio="brainstorming", user_prompt="예", provider="fake", is_marker=True, answer="예")
    res = h.handle_turn(req, provider=None, store=s)  # plan lock 확정은 LLM 호출 불필요
    assert h._load_state(s, "rb")["stage"] == "done"
    assert s.get_manifest("rb").step_status["brainstorming"] == "done"


def test_a_ready_bypass_runs_through_to_done():
    # bypass 경로: Stage A ready → _stage_b(first=True) → plan 생성 → ready&bypass → done
    from app.gateway.harness_brainstorming import BrainstormingHarness, REQUIRED_PLAN_FIELDS
    from app.gateway.harness import HarnessRequest
    h = BrainstormingHarness(); s = _store()
    full = "---\n" + "\n".join(f"{k}: v" for k in REQUIRED_PLAN_FIELDS) + "\n---\n계획"
    stub = StubProvider([
        {"text": json.dumps({"reply": "spec 정리완료", "document": "---\ngoal: x\n---\n본문", "ask": None, "ready": True})},
        {"text": json.dumps({"reply": "plan 초안", "document": full, "ask": None, "ready": True})},
    ])
    req = HarnessRequest(run_id="rb", studio="brainstorming", user_prompt="끝까지 자동", provider="fake", is_marker=True, bypass=True)
    res = h.handle_turn(req, provider=stub, store=s)
    assert s.get("/rb/brainstorming/plan.md") is not None
    assert h._load_state(s, "rb")["stage"] == "done"
    assert s.get_manifest("rb").step_status["brainstorming"] == "done"
