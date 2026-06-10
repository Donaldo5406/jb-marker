"""GateEnvelope 표준 봉투 (spec §4.1) — wire 직렬화 + HarnessResult/HTTP 가산 도입.

T1-P2 Task 1: 순수 가산 — 모든 하네스가 아직 gate=None이므로
HTTP 응답의 "gate"는 항상 null이어야 한다.
"""
from fastapi.testclient import TestClient

from app.gateway.harness import GateEnvelope, HarnessResult


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
