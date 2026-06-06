from fastapi.testclient import TestClient


def _client(monkeypatch):
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")  # 실 호출 방지 — mock 강제 전엔 빈 키로 예외 유도
    from app.server import create_app
    return TestClient(create_app())


def test_mock_true_forces_fake_text_provider(monkeypatch):
    """mock=true면 provider='anthropic'이어도 FakeProvider(echo)가 응답 — 실 키 호출 안 함."""
    client = _client(monkeypatch)
    rid = client.post("/runs", json={"title": "M"}).json()["run_id"]
    r = client.post("/gateway/run", json={
        "run_id": rid, "studio": "brainstorming", "prompt": "안녕",
        "provider": "anthropic", "is_marker": False, "mock": True,
    })
    assert r.status_code == 200
    # FakeProvider.complete는 "echo: <last>" 형태(providers/fake.py:17). passthrough가 그대로 영속.
    got = client.get(f"/vfs/{rid}/brainstorming/passthrough.md")
    assert "echo:" in got.json()["content_text"]


def test_mock_omitted_keeps_existing_behavior(monkeypatch):
    """mock 미동봉(기본 false) + provider='fake'면 기존 동작 유지(하위호환)."""
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    r = client.post("/gateway/run", json={
        "run_id": rid, "studio": "brainstorming", "prompt": "원문",
        "provider": "fake", "is_marker": False,
    })
    assert r.status_code == 200
    assert "원문" in client.get(f"/vfs/{rid}/brainstorming/passthrough.md").json()["content_text"]
