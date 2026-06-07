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


def test_review_demo_blocks_on_staged_violations(monkeypatch):
    """데모는 의도적으로 위반을 스테이징한다(vi/zh 예금자보호 고지 누락) → 검토가
    이를 잡아 critical → BLOCKED(위반 적발 시연, spec §1③). 검토는 R3까지 완주하고
    보고서·done 상태는 정상 기록된다. 교정 후 PASS 경로는 T7에서 별도 검증."""
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    _run(client, rid, "brainstorming", "정기예금 캠페인")
    bm = {s: True for s in ("S1", "S2a", "S2b", "S2c", "S3")}
    _run(client, rid, "design", "디자인 시작", action="advance", bypass_map=bm)
    # review는 호출당 한 단계 전진(R0→R1→R2→R3). 프론트 자동 루프와 동일하게 done까지 구동.
    gate: dict = {}
    last_step = None
    for _ in range(6):  # 정상 4단계 + 여유(무한루프 방지)
        r = _run(client, rid, "review", "검토 시작")
        assert r.status_code == 200
        meta = r.json().get("meta") or {}
        if meta.get("gate"):
            gate = meta["gate"]
        last_step = meta.get("step")
        if last_step == "R3":
            break
    # R3 종단 도달 + 스테이징 위반 적발 → BLOCKED(critical ≥ 1).
    assert last_step == "R3"
    assert gate.get("status") == "BLOCKED"
    assert gate.get("critical_count", 0) >= 1
    # 검토 보고서 생성 + state done 확인(BLOCKED여도 검토 단계 자체는 완주).
    report = client.get(f"/vfs/{rid}/review/report.md")
    assert report.status_code == 200
    state = client.get(f"/vfs/{rid}/review/_state.json")
    assert state.status_code == 200 and '"step": "done"' in state.json()["content_text"]
