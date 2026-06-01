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


def test_design_bypass_map_chains_to_done(monkeypatch, tmp_path):
    # bypass_map 전체 ON → 한 턴에 done까지(게이트 정지 없음)
    c = _client(monkeypatch, tmp_path)
    rid = c.post("/runs", json={"title": "B"}).json()["run_id"]
    c.put(f"/vfs/{rid}/brainstorming/plan.md", json={
        "content": "---\ncreative_direction:\n  aspect: \"1:1\"\nlanguages: [ko]\n---\n본문",
        "mime": "text/markdown"})
    r = c.post("/gateway/run", json={
        "run_id": rid, "studio": "design", "prompt": "", "provider": "fake",
        "is_marker": True, "action": "advance",
        "bypass_map": {"S1": True, "S2a": True, "S2b": True, "S2c": True, "S3": True}})
    assert r.status_code == 200
    assert r.json()["meta"]["step"] == "done"
