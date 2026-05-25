"""M1 DoD: run 생성 → AI 패스스루 → VFS 영속 → WS 서빙 → list/get 왕복."""
from app.server import create_app
from fastapi.testclient import TestClient


def test_golden_passthrough_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("JBM_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("VFS_BACKEND", "local")
    client = TestClient(create_app())

    run_id = client.post("/runs", json={"title": "골든"}).json()["run_id"]

    with client.websocket_connect(f"/ws/{run_id}") as wsconn:
        g = client.post("/gateway/run", json={
            "run_id": run_id, "studio": "brainstorming",
            "prompt": "핀테크 캠페인", "provider": "fake", "is_marker": False,
        })
        assert g.status_code == 200
        event = wsconn.receive_json()
        assert event["type"] == "artifact"
        out_path = event["path"]

    # VFS 영속 확인 (list + get 왕복)
    nodes = client.get(f"/vfs/{run_id}").json()["nodes"]
    assert any(n["path"] == out_path for n in nodes)
    got = client.get(f"/vfs/{run_id}/brainstorming/passthrough.md").json()
    assert "핀테크 캠페인" in got["content_text"]
    assert got["meta"]["source"] == "raw"
