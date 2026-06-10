"""GateEnvelope 표준 봉투 (spec §4.1) — wire 직렬화 + HarnessResult/HTTP 가산 도입.

T1-P2 Task 1: 순수 가산 — passthrough 등 미전환 하네스는 gate=None.
T1-P2 Task 2: brainstorming은 ask 대신 gate(kind="ask")를 채운다.
T1-P2 Task 3: design은 meta["gate"] 대신 gate(kind="confirm")를 채운다.
T1-P2 Task 4: review R3는 meta["gate"] 대신 gate(kind="status")+허용 actions를 채운다.
"""
import json

from fastapi.testclient import TestClient

from app.gateway.harness import GateEnvelope, HarnessResult
from app.providers.base import ProviderResponse


class StubProvider:
    """미리 정한 JSON 텍스트를 순서대로 반환(LLM 대체) — test_brainstorming_harness.py 패턴."""
    def __init__(self, responses): self._r = list(responses); self.calls = []
    def complete(self, messages, *, model, system=None, tools=None, **kw):
        self.calls.append({"system": system, "tools": tools, "messages": messages})
        r = self._r.pop(0)
        return ProviderResponse(text=r["text"], model=model,
                               citations=r.get("citations", []), usage=r.get("usage"))


def test_to_dict_omits_none_fields():
    env = GateEnvelope(kind="ask", trigger="a", question="q",
                       options=["x"], actions=["answer"])
    assert env.to_dict() == {"kind": "ask", "actions": ["answer"],
                             "trigger": "a", "question": "q", "options": ["x"]}


def test_to_dict_status_kind():
    env = GateEnvelope(kind="status", status="WARN",
                       critical_count=0, warning_count=2,
                       actions=["ack", "regenerate", "restart"])
    d = env.to_dict()
    assert set(d.keys()) == {"kind", "actions", "status",
                             "critical_count", "warning_count"}
    assert d["kind"] == "status"
    assert d["actions"] == ["ack", "regenerate", "restart"]
    assert d["status"] == "WARN"
    assert d["critical_count"] == 0
    assert d["warning_count"] == 2


def test_harness_result_gate_default_none():
    assert HarnessResult(text="t", output_path="/p", meta={}).gate is None


def test_gateway_response_includes_gate_key(monkeypatch, tmp_path):
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("JBM_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "true")
    from app.server import create_app
    c = TestClient(create_app())
    rid = c.post("/runs", json={"title": "g"}).json()["run_id"]
    r = c.post("/gateway/run", json={
        "run_id": rid, "studio": "brainstorming",
        "prompt": "hi", "provider": "fake", "is_marker": False,
    })
    assert r.status_code == 200
    body = r.json()
    assert "gate" in body
    assert body["gate"] is None


def test_brainstorming_mock_turn_returns_ask_gate(monkeypatch, tmp_path):
    """T1-P2 Task 2: 브레인 mock 1턴(demo provider는 첫 턴에 질문(a)을 보장)
    → HTTP 응답 gate가 kind="ask" 봉투로 채워진다."""
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("JBM_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "true")
    from app.server import create_app
    c = TestClient(create_app())
    rid = c.post("/runs", json={"title": "g"}).json()["run_id"]
    r = c.post("/gateway/run", json={
        "run_id": rid, "studio": "brainstorming",
        "prompt": "정기예금 캠페인 기획하자", "provider": "anthropic",
        "is_marker": True, "mock": True,
    })
    assert r.status_code == 200
    gate = r.json()["gate"]
    assert gate is not None
    assert gate["kind"] == "ask"
    assert gate["actions"] == ["answer"]
    assert "trigger" in gate


def test_brainstorming_events_carry_gate(monkeypatch, tmp_path):
    """T1-P2 Task 2 리뷰 후속: WS로 릴레이되는 HarnessResult.events에
    {"type":"gate","gate":{...}} 이벤트가 실리고 askuser는 소멸했는지 직접 단언."""
    monkeypatch.setenv("JBM_STORAGE_DIR", str(tmp_path))
    from app.gateway.harness import HarnessRequest
    from app.gateway.harness_brainstorming import BrainstormingHarness
    from app.vfs.local import LocalVfsStore
    h = BrainstormingHarness()
    s = LocalVfsStore(); s.create_run("rb")
    stub = StubProvider([{"text": json.dumps(
        {"reply": "주력 채널은 무엇인가요?",
         "document": "---\ngoal: 적금 캠페인\n---\n# 기획",
         "ask": {"trigger": "a", "question": "주력 채널?", "options": ["카톡", "이메일"]},
         "ready": False})}])
    req = HarnessRequest(run_id="rb", studio="brainstorming",
                         user_prompt="30대 적금 캠페인", provider="fake", is_marker=True)
    res = h.handle_turn(req, provider=stub, store=s)
    assert res.gate is not None and res.gate.kind == "ask"
    gate_events = [e for e in res.events if e.get("type") == "gate"]
    assert len(gate_events) == 1
    assert gate_events[0]["gate"]["kind"] == "ask"
    assert gate_events[0]["gate"]["actions"] == ["answer"]
    assert not [e for e in res.events if e.get("type") == "askuser"]


def _design_store(tmp_path, run_id="rd"):
    """test_design_gate.py의 _store 패턴 — plan.md 시드된 LocalVfsStore."""
    from app.vfs.local import LocalVfsStore
    s = LocalVfsStore(storage_dir=str(tmp_path))
    s.create_run(run_id, languages=["ko"])
    s.put(f"/{run_id}/brainstorming/plan.md",
          "---\ncreative_direction:\n  palette: [\"#0A84FF\"]\n  font: Inter\n  aspect: \"1:1\"\n"
          "factsheet:\n  rate: \"연 3.5%\"\n"
          "material_matrix: [{channel: instagram, lang: ko}]\nlanguages: [ko]\n---\n본문",
          source="marker", mime="text/markdown")
    return s


def _design_req(run_id="rd", action="advance"):
    from app.gateway.harness import HarnessRequest
    return HarnessRequest(run_id=run_id, studio="design", user_prompt="",
                          provider="fake", is_marker=True, action=action)


def test_design_gate_stop_returns_confirm_envelope(tmp_path):
    """T1-P2 Task 3: design 게이트 정지 → gate=GateEnvelope(kind="confirm"),
    meta["gate"] 구 신호는 소멸."""
    from app.gateway.harness_design import DesignHarness
    from app.providers.fake import FakeProvider
    s = _design_store(tmp_path)
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_design_req(), provider=FakeProvider(), store=s)
    assert res.gate is not None
    assert res.gate.kind == "confirm"
    assert res.gate.step == "S1"                       # S0 비게이트 통과 후 S1 정지
    assert res.gate.actions == ["confirm", "regenerate"]
    assert "gate" not in res.meta


def test_actions_for_status_table():
    """T1-P2 Task 4: 게이트 status별 허용 후속 액션 테이블 (spec §4.2)."""
    from app.gateway.harness_review import _actions_for
    assert _actions_for("WARN") == ["ack", "regenerate", "restart"]
    assert _actions_for("BLOCKED") == ["regenerate", "restart"]
    assert _actions_for("PASS") == []


def _review_store(tmp_path, run_id="rr"):
    """test_review_harness.py의 _setup_run 패턴 — plan.md·design 산출·렌더 시드(모노링구얼 ko)."""
    from app.vfs.factory import make_local_store
    s = make_local_store(tmp_path)
    s.create_run(run_id, languages=["ko"])
    s.put(f"/{run_id}/brainstorming/plan.md",
          "---\nlanguages: [ko]\ndisclosures: []\n---\n# Plan\n",
          source="marker", mime="text/markdown")
    s.put(f"/{run_id}/design/final/ko/main.scene",
          json.dumps({"copy": {"ko": {"headline": "쉽고 빠르게"}}}),
          source="marker", mime="application/json")
    s.put(f"/{run_id}/design/metadata.md", "", source="marker", mime="text/markdown")
    s.put(f"/{run_id}/design/design-system/components/visual/v1.png",
          b"\x89PNG\x00fake", source="gemini", mime="image/png")
    s.put(f"/{run_id}/review/_render/ko.png", b"\x89PNG-ko",
          source="frontend", mime="image/png")
    return s


def test_review_r3_returns_status_gate_envelope(tmp_path, make_scripted):
    """T1-P2 Task 4: review R3 종단 → gate=GateEnvelope(kind="status")+허용 actions,
    meta["gate"] 구 신호는 소멸. (warning 1건·트리거 0 → 결정론 WARN)"""
    from app.gateway.harness import HarnessRequest
    from app.gateway.harness_review import ReviewHarness
    from app.providers.fake import FakeProvider
    s = _review_store(tmp_path)
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="rr", studio="review", user_prompt="검토 시작",
                         provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=s)              # R0
    h.handle_turn(req, provider=make_scripted(complete_responses=[    # R1: warning 1건
        ProviderResponse(text=('{"findings":[{"location":{"slot":"headline","lang":"ko"},'
                               '"clause":"§X","official_source_url":"https://law.go.kr/x",'
                               '"severity":"warning","evidence":"x"}]}'), model="x")]),
        store=s)
    h.handle_turn(req, provider=FakeProvider(), store=s)              # R2 (모노링구얼 스킵)
    res = h.handle_turn(req, provider=make_scripted(complete_responses=[
        ProviderResponse(text='{"recommendations":[],"conflicts_resolved":[]}',
                         model="x")]), store=s)                        # R3 종단
    assert res.gate is not None
    assert res.gate.kind == "status"
    assert res.gate.status == "WARN"
    assert res.gate.critical_count == 0
    assert res.gate.warning_count >= 1
    assert res.gate.actions == ["ack", "regenerate", "restart"]
    assert "gate" not in res.meta


def test_design_bypass_chain_done_has_no_gate(tmp_path):
    """T1-P2 Task 3: 전 step bypass 연쇄 done → gate=None,
    auto_advanced는 meta 평탄 키로 이동, meta["gate"] 소멸."""
    from app.gateway.harness_design import DesignHarness
    from app.providers.fake import FakeProvider
    s = _design_store(tmp_path)
    s.put("/rd/design/_state.json", json.dumps(
        {"step": "S1", "gate": None, "confirmed": {},
         "bypass": {k: True for k in ("S1", "S2a", "S2b", "S2c", "S3")},
         "languages": ["ko"], "pending_ask": None}),
        source="marker", mime="application/json")
    s.put("/rd/design/rough/layout.spec.json", json.dumps({"copy": {"ko": {}}}),
          source="marker", mime="application/json")
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_design_req(), provider=FakeProvider(), store=s)
    assert res.meta["step"] == "done"
    assert res.gate is None
    assert res.meta["auto_advanced"] == ["S1", "S2a", "S2b", "S2c", "S3"]
    assert "gate" not in res.meta
