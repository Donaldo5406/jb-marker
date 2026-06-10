"""S2a 이미지 생성 비용이 usage 로그에 기록되는지 — 주입 provider 래핑 회귀 가드 (spec §7-2)."""
from fastapi.testclient import TestClient


def _client(monkeypatch, tmp_path):
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("JBM_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "true")
    from app.server import create_app
    return TestClient(create_app())


def test_design_image_call_recorded_in_usage(monkeypatch, tmp_path):
    c = _client(monkeypatch, tmp_path)
    rid = c.post("/runs", json={"title": "u"}).json()["run_id"]
    c.put(f"/vfs/{rid}/brainstorming/plan.md", json={
        "content": "---\ncreative_direction:\n  aspect: \"1:1\"\nlanguages: [ko]\n---\n본문",
        "mime": "text/markdown"})
    r = c.post("/gateway/run", json={
        "run_id": rid, "studio": "design", "prompt": "", "provider": "fake",
        "is_marker": True, "action": "advance", "mock": True,
        "bypass_map": {"S1": True, "S2a": True, "S2b": True, "S2c": True, "S3": True}})
    assert r.status_code == 200
    summary = c.get(f"/runs/{rid}/usage").json()
    kinds = {e["kind"] for e in summary["entries"]}
    assert "image" in kinds   # S2a generate_image가 기록됨 (래핑 전엔 텍스트만 기록)
