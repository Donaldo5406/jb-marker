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
