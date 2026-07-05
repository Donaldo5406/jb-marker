"""폐루프 D3 — 심의 통과해야만 dispatch(백엔드 강제).
- 실사용(mock=false): PASS 또는 **ack된 WARN**만 발송(경고 확인=사람 판단).
- mock 시연(mock=true): PASS/WARN 모두 발송(ack 불요) — BLOCKED/미실행만 차단.
"""
import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def gate_client(monkeypatch, tmp_path):
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("JBM_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "1")
    from app.server import create_app
    return TestClient(create_app())


def _prep_run(client, review_status=None, acknowledged=False):
    rid = client.post("/runs", json={}).json()["run_id"]
    store = client.app.state.store
    client.post(f"/runs/{rid}/deploy/setup",
                json={"selected_providers": ["sms"], "languages": ["ko"]})
    client.post(f"/runs/{rid}/deploy/eligibility", json={})
    if review_status:
        store.set_step_status(rid, "review", review_status)
    if acknowledged:
        store.put(f"/{rid}/review/_state.json",
                  json.dumps({"acknowledged": True}), source="marker",
                  mime="application/json")
    return rid


def _dispatch(client, rid, mock=True):
    return client.post(f"/runs/{rid}/deploy/dispatch",
                       json={"confirmed": True, "mock": mock})


def test_dispatch_blocked_without_review(gate_client):
    rid = _prep_run(gate_client)                       # review 미실행 — mock도 차단
    r = _dispatch(gate_client, rid)
    assert r.status_code == 409
    assert "review gate" in r.json()["detail"]


def test_dispatch_blocked_on_blocked_review(gate_client):
    rid = _prep_run(gate_client, review_status="BLOCKED")   # BLOCKED은 mock에서도 차단
    assert _dispatch(gate_client, rid).status_code == 409


def test_dispatch_mock_allows_unacked_warn(gate_client):
    """mock 시연: 미확인 WARN도 발송 허용(ack 불요 — 데모 마찰 제거)."""
    rid = _prep_run(gate_client, review_status="WARN", acknowledged=False)
    assert _dispatch(gate_client, rid, mock=True).status_code == 200


def test_dispatch_live_blocks_unacked_warn(gate_client):
    """실사용(mock=false): 미확인 WARN은 여전히 409(내부통제 — 사람 확인 필수)."""
    rid = _prep_run(gate_client, review_status="WARN", acknowledged=False)
    r = _dispatch(gate_client, rid, mock=False)
    assert r.status_code == 409 and "ack" in r.json()["detail"]


def test_dispatch_live_allows_acked_warn(gate_client):
    rid = _prep_run(gate_client, review_status="WARN", acknowledged=True)
    assert _dispatch(gate_client, rid, mock=False).status_code == 200


def test_dispatch_allows_pass(gate_client):
    rid = _prep_run(gate_client, review_status="PASS")
    r = _dispatch(gate_client, rid)
    assert r.status_code == 200 and r.json()["step_status"] == "PASS"
