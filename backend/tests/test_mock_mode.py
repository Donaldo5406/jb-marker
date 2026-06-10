from fastapi.testclient import TestClient


def _client(monkeypatch):
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")  # 실 호출 방지 — mock 강제 전엔 빈 키로 예외 유도
    from app.server import create_app
    return TestClient(create_app())


def test_mock_true_forces_demo_text_provider(monkeypatch):
    """mock=true면 provider='anthropic'이어도 DemoProvider가 응답 — 실 키 호출 안 함."""
    client = _client(monkeypatch)
    rid = client.post("/runs", json={"title": "M"}).json()["run_id"]
    r = client.post("/gateway/run", json={
        "run_id": rid, "studio": "brainstorming", "prompt": "안녕",
        "provider": "anthropic", "is_marker": False, "mock": True,
    })
    assert r.status_code == 200
    # passthrough가 DemoProvider.complete 결과를 그대로 영속(미매칭 system → 빈 reply JSON).
    got = client.get(f"/vfs/{rid}/brainstorming/_passthrough.md")
    assert got.status_code == 200


def test_mock_omitted_keeps_existing_behavior(monkeypatch):
    """mock 미동봉(기본 false) + provider='fake'면 기존 동작 유지(하위호환)."""
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    r = client.post("/gateway/run", json={
        "run_id": rid, "studio": "brainstorming", "prompt": "원문",
        "provider": "fake", "is_marker": False,
    })
    assert r.status_code == 200
    assert "원문" in client.get(f"/vfs/{rid}/brainstorming/_passthrough.md").json()["content_text"]


def test_design_mock_injects_fake_image_provider(monkeypatch):
    """mock=true면 DesignHarness가 fake image_provider를 받는다(1x1 PNG 폴백, 무료)."""
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "1")
    import app.server as srv
    captured = {}
    real = srv.DesignHarness

    class SpyDesign(real):
        def __init__(self, *a, image_provider=None, **k):
            captured["img"] = image_provider
            super().__init__(*a, image_provider=image_provider, **k)

    monkeypatch.setattr(srv, "DesignHarness", SpyDesign)
    client = TestClient(srv.create_app())
    rid = client.post("/runs", json={}).json()["run_id"]
    client.post("/gateway/run", json={
        "run_id": rid, "studio": "design", "prompt": "x",
        "provider": "anthropic", "is_marker": True, "mock": True,
    })
    assert captured["img"] is not None and captured["img"].name == "demo"


def test_review_mock_injects_fake_vision_provider(monkeypatch):
    """mock=true면 ReviewHarness가 fake vision_provider를 받는다."""
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "1")
    import app.server as srv
    import app.gateway.harness_review as hr
    captured = {}
    real = hr.ReviewHarness

    class SpyReview(real):
        def __init__(self, *a, vision_provider=None, **k):
            captured["vision"] = vision_provider
            super().__init__(*a, vision_provider=vision_provider, **k)

    monkeypatch.setattr(hr, "ReviewHarness", SpyReview)
    client = TestClient(srv.create_app())
    rid = client.post("/runs", json={}).json()["run_id"]
    client.post("/gateway/run", json={
        "run_id": rid, "studio": "review", "prompt": "검토",
        "provider": "anthropic", "is_marker": True, "mock": True,
    })
    assert captured["vision"] is not None and captured["vision"].name == "demo"


def test_design_no_mock_uses_google_image_provider(monkeypatch):
    """mock 없으면 기존대로 google image_provider(회귀 가드)."""
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "1")
    import app.server as srv
    captured = {}
    real = srv.DesignHarness

    class SpyDesign(real):
        def __init__(self, *a, image_provider=None, **k):
            captured["img"] = image_provider
            super().__init__(*a, image_provider=image_provider, **k)

    monkeypatch.setattr(srv, "DesignHarness", SpyDesign)
    client = TestClient(srv.create_app())
    rid = client.post("/runs", json={}).json()["run_id"]
    # provider=fake → text는 키 없이 동작(실 호출 회피). image_provider는 mock=false라 google이어야.
    client.post("/gateway/run", json={
        "run_id": rid, "studio": "design", "prompt": "x",
        "provider": "fake", "is_marker": True,
    })
    assert captured["img"].name == "google"


def test_advisor_mock_forces_scripted(monkeypatch):
    """ADVISOR_MODE=live여도 mock=true면 scripted(LLM 없음) — 응답에 _usage 없음."""
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("ADVISOR_MODE", "live")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")  # live+빈키면 422 — mock 강제 전 실 호출 방지
    import app.server as srv
    client = TestClient(srv.create_app())
    rid = client.post("/runs", json={}).json()["run_id"]
    # advisor도 is_entitled 단일 choke(override 존중) — 여기선 override 없이 dev pass로 통과.
    client.put("/entitlement", json={"marker": True})
    # package copy.meta.json 준비(ctx_raw). channel은 package_id 접두("sms").
    client.put(f"/vfs/{rid}/deploy/packages/sms_ko/copy.meta.json",
               json={"content": "{}"})
    r = client.post(f"/runs/{rid}/deploy/advisor/chat", json={
        "package_id": "sms_ko", "message": "짧게 줄여줘", "mock": True,
    })
    assert r.status_code == 200
    assert "_usage" not in r.json()   # scripted는 usage 미노출(server.py:501 분기)
