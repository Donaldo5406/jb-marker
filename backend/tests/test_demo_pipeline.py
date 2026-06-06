"""demo(mock)로 BrainStorming→Design→Review 전 구간 완주 — 끝까지 도는 mock 검증."""
from fastapi.testclient import TestClient


def _client(monkeypatch):
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    from app.server import create_app
    return TestClient(create_app())


def _run(client, rid, studio, prompt, **kw):
    body = {"run_id": rid, "studio": studio, "prompt": prompt,
            "provider": "anthropic", "is_marker": True, "mock": True, "bypass": True}
    body.update(kw)
    return client.post("/gateway/run", json=body)


def test_brainstorming_demo_produces_spec_and_plan(monkeypatch):
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    r = _run(client, rid, "brainstorming", "정기예금 캠페인")
    assert r.status_code == 200
    # bypass → Stage A ready → Stage B 자동 진입 → plan 생성, brainstorming done.
    spec = client.get(f"/vfs/{rid}/brainstorming/spec.md")
    plan = client.get(f"/vfs/{rid}/brainstorming/plan.md")
    assert spec.status_code == 200 and "goal:" in spec.json()["content_text"]
    assert plan.status_code == 200 and "creative_direction:" in plan.json()["content_text"]


def test_design_demo_produces_layout_and_visual(monkeypatch):
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    _run(client, rid, "brainstorming", "정기예금 캠페인")
    # design: bypass_map으로 전 step OFF → 한 턴 연쇄.
    bm = {s: True for s in ("S1", "S2a", "S2b", "S2c", "S3")}
    r = _run(client, rid, "design", "디자인 시작", action="advance", bypass_map=bm)
    assert r.status_code == 200
    ls = client.get(f"/vfs/{rid}/design/rough/layout.spec.json")
    assert ls.status_code == 200 and "slots" in ls.json()["content_text"]
    png = client.get(f"/vfs/{rid}/design/design-system/components/visual/v1.png")
    assert png.status_code == 200


def test_review_demo_reaches_pass(monkeypatch):
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    _run(client, rid, "brainstorming", "정기예금 캠페인")
    bm = {s: True for s in ("S1", "S2a", "S2b", "S2c", "S3")}
    _run(client, rid, "design", "디자인 시작", action="advance", bypass_map=bm)
    r = _run(client, rid, "review", "검토 시작")
    assert r.status_code == 200
    # 빈 findings → critical 0 → gate PASS(또는 WARN). BLOCK이 아니어야 deploy 진입 가능.
    gate = (r.json().get("meta") or {}).get("gate") or {}
    assert gate.get("status") in ("PASS", "WARN", "", None)
