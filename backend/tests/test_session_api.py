import json


def _make_run(client):
    r = client.post("/runs", json={"title": "t"})
    return r.json()["run_id"]


def test_gateway_turn_creates_session_json(client):
    run_id = _make_run(client)
    client.post("/gateway/run", json={
        "run_id": run_id, "studio": "brainstorming",
        "prompt": "안녕", "provider": "fake", "is_marker": False,
    })
    # 무상태 PassthroughHarness라도 서버가 touch → _session.json 생성
    node = client.get(f"/vfs/{run_id}/brainstorming/_session.json")
    assert node.status_code == 200
    rec = json.loads(node.json()["content_text"])
    assert rec["studio"] == "brainstorming"
    assert rec["status"] == "active"


def test_heartbeat_endpoint_reports_liveness(client):
    run_id = _make_run(client)
    client.post("/gateway/run", json={
        "run_id": run_id, "studio": "design",
        "prompt": "x", "provider": "fake", "is_marker": False,
    })
    r = client.get(f"/runs/{run_id}/session/design")
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "heartbeat"
    assert body["exists"] is True
    assert body["liveness"] == "healthy"


def test_heartbeat_missing_studio_exists_false(client):
    run_id = _make_run(client)
    r = client.get(f"/runs/{run_id}/session/review")
    assert r.json() == {"kind": "heartbeat", "exists": False,
                        "status": None, "resumable": False}


def test_resume_endpoint_restores(client):
    run_id = _make_run(client)
    client.post("/gateway/run", json={
        "run_id": run_id, "studio": "design",
        "prompt": "x", "provider": "fake", "is_marker": False,
    })
    r = client.post(f"/runs/{run_id}/session/design/resume")
    assert r.json()["kind"] == "restored"


def test_resume_missing_returns_expired(client):
    run_id = _make_run(client)
    r = client.post(f"/runs/{run_id}/session/deploy/resume")
    assert r.json()["kind"] == "expired"


def test_list_endpoint_lists_sessions(client):
    run_id = _make_run(client)
    for st in ("brainstorming", "design"):
        client.post("/gateway/run", json={
            "run_id": run_id, "studio": st,
            "prompt": "x", "provider": "fake", "is_marker": False,
        })
    r = client.get(f"/runs/{run_id}/sessions")
    body = r.json()
    assert body["kind"] == "session_list"
    assert {s["studio"] for s in body["sessions"]} == {"brainstorming", "design"}


def test_suspend_endpoint(client):
    run_id = _make_run(client)
    client.post("/gateway/run", json={
        "run_id": run_id, "studio": "design",
        "prompt": "x", "provider": "fake", "is_marker": False,
    })
    r = client.post(f"/runs/{run_id}/session/design/suspend")
    assert r.json() == {"kind": "suspended", "status": "suspended"}


def test_turn_after_suspend_emits_restored_event_in_meta(client):
    run_id = _make_run(client)
    client.post("/gateway/run", json={
        "run_id": run_id, "studio": "design",
        "prompt": "x", "provider": "fake", "is_marker": False,
    })
    client.post(f"/runs/{run_id}/session/design/suspend")  # 명시 종료
    r = client.post("/gateway/run", json={
        "run_id": run_id, "studio": "design",
        "prompt": "다시", "provider": "fake", "is_marker": False,
    })
    # 응답 meta에 재활성 신호
    assert r.json()["meta"].get("session_event") == "restored"


def test_turn_on_active_has_no_restored_event(client):
    run_id = _make_run(client)
    r = client.post("/gateway/run", json={
        "run_id": run_id, "studio": "design",
        "prompt": "x", "provider": "fake", "is_marker": False,
    })
    assert r.json()["meta"].get("session_event") is None
