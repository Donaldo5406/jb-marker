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
