from fastapi.testclient import TestClient

from app.server import create_app


def _client(monkeypatch, tmp_path):
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("JBM_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "true")
    return TestClient(create_app())


def test_design_marker_routes_to_design_harness(monkeypatch, tmp_path):
    c = _client(monkeypatch, tmp_path)
    run_id = c.post("/runs", json={"title": "t"}).json()["run_id"]
    c.put(f"/vfs/{run_id}/brainstorming/plan.md", json={
        "content": "---\ncreative_direction:\n  palette: [\"#0A84FF\"]\n  aspect: \"1:1\"\n"
                   "material_matrix: [{channel: instagram, lang: ko}]\nlanguages: [ko]\n---\n본문",
        "mime": "text/markdown"})
    r = c.post("/gateway/run", json={
        "run_id": run_id, "studio": "design", "prompt": "시작",
        "provider": "fake", "is_marker": True, "action": "advance"})
    assert r.status_code == 200
    tok = c.get(f"/vfs/{run_id}/design/design-system/tokens.json")
    assert tok.status_code == 200
