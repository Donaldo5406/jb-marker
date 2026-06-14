from fastapi.testclient import TestClient

import app.gateway.registry as registry_mod


def _client(monkeypatch):
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")  # 실 호출 방지 — mock 강제 전엔 빈 키로 예외 유도
    from app.server import create_app
    return TestClient(create_app())


def test_mock_true_routes_marker_harness_not_passthrough(monkeypatch):
    """mock=true면 is_marker=false(프론트 기본 모델 Claude)여도 Marker 하네스로 라우팅된다.

    시연 footgun 회귀 가드: 예전엔 mock이 provider만 demo로 바꾸고 is_marker는 그대로라,
    기본 모델(Claude=is_marker:false)이면 PassthroughHarness로 빠져 _passthrough.md만 쓰고
    빈 echo → 프론트가 _messages/_state.json을 404로 못 읽어 챗이 멈췄다. 이제 mock=true는
    Marker 하네스를 강제 → BrainStorming stage A의 ask 게이트와 _state.json이 생성된다."""
    client = _client(monkeypatch)
    rid = client.post("/runs", json={"title": "M"}).json()["run_id"]
    r = client.post("/gateway/run", json={
        "run_id": rid, "studio": "brainstorming", "prompt": "정기예금 캠페인 만들어줘",
        "provider": "anthropic", "is_marker": False, "mock": True,
    })
    assert r.status_code == 200
    body = r.json()
    # Marker(BrainStorming) 하네스가 동작 → stage A ask 게이트 + source=marker.
    assert (body.get("gate") or {}).get("kind") == "ask"
    assert body["meta"]["source"] == "marker"
    # passthrough 경로가 아님 → _passthrough.md 없음, 대신 marker 상태/대화가 영속.
    assert client.get(f"/vfs/{rid}/brainstorming/_passthrough.md").status_code == 404
    assert client.get(f"/vfs/{rid}/brainstorming/_state.json").status_code == 200


def test_mock_true_bypasses_entitlement_when_free(monkeypatch):
    """mock=true면 무료(entitlement OFF)여도 402가 아니라 Marker 하네스가 무료로 완주한다.

    시연용 Mock은 '자유·결정적 데모'가 목적 → 유료 게이트(check_entitlement)를 우회한다.
    design(프론트가 is_marker:true 전송)도 entitlement 없이 통과해야 한다."""
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "0")  # 유료 게이트 활성(우회 없음)
    from app.server import create_app
    client = TestClient(create_app())
    rid = client.post("/runs", json={}).json()["run_id"]
    # entitlement PUT 하지 않음 → 무료 사용자. mock=true가 게이트를 뚫어야 200.
    r = client.post("/gateway/run", json={
        "run_id": rid, "studio": "design", "prompt": "디자인 시작",
        "provider": "anthropic", "is_marker": True, "mock": True,
    })
    assert r.status_code == 200, f"mock인데 402로 막힘: {r.status_code} {r.text[:200]}"


def test_no_mock_free_user_still_blocked_402(monkeypatch):
    """회귀 가드: mock 없이 is_marker=true + 무료면 종전대로 402(유료 게이트 유지)."""
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "0")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    from app.server import create_app
    client = TestClient(create_app())
    rid = client.post("/runs", json={}).json()["run_id"]
    r = client.post("/gateway/run", json={
        "run_id": rid, "studio": "design", "prompt": "x",
        "provider": "anthropic", "is_marker": True,
    })
    assert r.status_code == 402


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
    real = registry_mod.DesignHarness

    class SpyDesign(real):
        def __init__(self, *a, image_provider=None, **k):
            captured["img"] = image_provider
            super().__init__(*a, image_provider=image_provider, **k)

    monkeypatch.setattr(registry_mod, "DesignHarness", SpyDesign)
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
    real = registry_mod.DesignHarness

    class SpyDesign(real):
        def __init__(self, *a, image_provider=None, **k):
            captured["img"] = image_provider
            super().__init__(*a, image_provider=image_provider, **k)

    monkeypatch.setattr(registry_mod, "DesignHarness", SpyDesign)
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
    assert "_usage" not in r.json()   # scripted는 usage 미노출(routers/deploy.py 분기)


def test_gateway_accepts_null_medium(monkeypatch):
    """프론트 advance 계열 요청은 medium을 빠뜨려 null로 보낸다(lib/api: `medium ?? null`).

    백엔드 GatewayRun.medium은 Literal["image","video"]라 '키 부재'엔 기본값 'image'가
    먹지만 **명시적 null**은 검증 실패(422)였다 — design '다음 단계 →'(action="advance")가
    라이브에서 무반응이던 근본 원인(프론트↔백 계약 불일치). medium=null은 'image'로
    정규화돼 200이어야 한다(하위호환 회귀 가드)."""
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    r = client.post("/gateway/run", json={
        "run_id": rid, "studio": "design", "prompt": "",
        "provider": "anthropic", "is_marker": True, "action": "advance",
        "mock": True, "medium": None,
    })
    assert r.status_code == 200, f"medium=null인데 거부됨: {r.status_code} {r.text[:200]}"
