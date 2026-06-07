def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_run_and_list(client):
    r = client.post("/runs", json={"title": "캠페인"})
    assert r.status_code == 200
    run_id = r.json()["run_id"]

    g = client.post("/gateway/run", json={
        "run_id": run_id, "studio": "brainstorming",
        "prompt": "아이디어", "provider": "fake", "is_marker": False,
    })
    assert g.status_code == 200
    out_path = g.json()["output_path"]

    lst = client.get(f"/vfs/{run_id}", params={"prefix": f"/{run_id}/brainstorming"})
    assert any(n["path"] == out_path for n in lst.json()["nodes"])

    got = client.get(f"/vfs/{run_id}/brainstorming/_passthrough.md")
    assert got.status_code == 200
    assert "아이디어" in got.json()["content_text"]


def test_put_text_via_editor(client):
    run_id = client.post("/runs", json={}).json()["run_id"]
    r = client.put(f"/vfs/{run_id}/design/notes.md", json={"content": "메모"})
    assert r.status_code == 200
    assert client.get(f"/vfs/{run_id}/design/notes.md").json()["content_text"] == "메모"


def test_get_runs_lists_created_runs():
    from fastapi.testclient import TestClient
    from app.server import create_app
    client = TestClient(create_app())
    r1 = client.post("/runs", json={"title": "A"})
    rid = r1.json()["run_id"]
    resp = client.get("/runs")
    assert resp.status_code == 200
    runs = resp.json()["runs"]
    assert any(x["run_id"] == rid and x["title"] == "A" for x in runs)
    assert "step_status" in runs[0] and "created_at" in runs[0]


def test_entitlement_toggle_gates_marker(monkeypatch):
    # per-user 게이트 검증 — env override는 0으로 둬 user_id(local=demo) 기반 토글만 본다.
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "0")
    monkeypatch.setenv("VFS_BACKEND", "local")
    from fastapi.testclient import TestClient
    from app.server import create_app
    client = TestClient(create_app())
    rid = client.post("/runs", json={"title": "E"}).json()["run_id"]
    # 기본(무료): Marker 호출 → 402
    body = {"run_id": rid, "studio": "brainstorming", "prompt": "안녕",
            "provider": "fake", "is_marker": True}
    assert client.post("/gateway/run", json=body).status_code == 402
    # 초기 상태 조회
    assert client.get("/entitlement").json()["marker"] is False
    # 토글 ON (demo user에 dev_pass 부여)
    assert client.put("/entitlement", json={"marker": True}).json()["marker"] is True
    # 이제 Marker 통과 (gateway가 user_id=demo의 entitlement.check를 평가)
    assert client.post("/gateway/run", json=body).status_code == 200


def test_put_vfs_infers_json_mime():
    from fastapi.testclient import TestClient
    from app.server import create_app
    client = TestClient(create_app())
    rid = client.post("/runs", json={"title": "M"}).json()["run_id"]
    resp = client.put(f"/vfs/{rid}/brainstorming/data.json", json={"content": "{\"k\":1}"})
    assert resp.status_code == 200
    assert resp.json()["mime"] == "application/json"
    # 명시 mime 우선 (VFS 경로는 /{runId}/{studio}/... 규약을 따른다)
    resp2 = client.put(f"/vfs/{rid}/brainstorming/note.md", json={"content": "# hi", "mime": "text/markdown"})
    assert resp2.json()["mime"] == "text/markdown"


def test_brain_marker_uses_brainstorming_harness_and_writes_spec():
    from fastapi.testclient import TestClient
    from app.server import create_app
    client = TestClient(create_app())
    client.put("/entitlement", json={"marker": True})  # Marker 허용
    rid = client.post("/runs", json={"title": "B"}).json()["run_id"]
    body = {"run_id": rid, "studio": "brainstorming", "prompt": "적금 캠페인",
            "provider": "fake", "is_marker": True}
    r = client.post("/gateway/run", json=body)
    assert r.status_code == 200
    nodes = client.get(f"/vfs/{rid}").json()["nodes"]
    paths = [n["path"] for n in nodes]
    # 브레인스토밍 하네스 사용 신호(passthrough는 _state.json을 만들지 않음).
    # fake provider는 비-JSON echo라 document가 비어 spec.md는 쓰지 않음(대화-우선) —
    # 실제 spec 생성은 test_brainstorming_harness가 StubProvider로 커버.
    assert f"/{rid}/brainstorming/_state.json" in paths
    assert "ask" in r.json()


def test_free_brain_uses_passthrough():
    from fastapi.testclient import TestClient
    from app.server import create_app
    client = TestClient(create_app())
    rid = client.post("/runs", json={"title": "P"}).json()["run_id"]
    body = {"run_id": rid, "studio": "brainstorming", "prompt": "hi", "provider": "fake", "is_marker": False}
    r = client.post("/gateway/run", json=body)
    assert r.status_code == 200
    assert r.json()["output_path"].endswith("/_passthrough.md")


def test_vfs_put_base64_decodes_to_bytes(client):
    """T17 가산 — content_encoding="base64"면 bytes 라운드트립.

    sceneRender.uploadRender가 PNG를 base64로 인코드해 PUT /vfs/{run_id}/{rest}로
    보낼 때, 백엔드가 bytes로 디코드해 blob으로 저장하고 GET이 원본 바이트를
    반환해야 R1 vision 단계에서 정상 읽기가 가능하다.
    """
    import base64
    rid = client.post("/runs", json={"title": "B64"}).json()["run_id"]
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00\x01\x02\x03fakecontent"
    b64 = base64.b64encode(png_bytes).decode("ascii")
    r = client.put(f"/vfs/{rid}/review/_render/ko.png", json={
        "content": b64,
        "content_encoding": "base64",
        "mime": "image/png",
    })
    assert r.status_code == 200, r.text
    # GET → blob 라운드트립 (bytes 그대로)
    r2 = client.get(f"/vfs/{rid}/review/_render/ko.png")
    assert r2.status_code == 200
    assert r2.content == png_bytes
    assert r2.headers.get("content-type", "").startswith("image/png")


def test_vfs_put_text_path_unchanged_when_no_encoding(client):
    """T17 가산 회귀 — content_encoding 미지정이면 기존 텍스트 경로 그대로."""
    rid = client.post("/runs", json={"title": "T"}).json()["run_id"]
    r = client.put(f"/vfs/{rid}/design/note.md", json={"content": "메모"})
    assert r.status_code == 200
    assert client.get(f"/vfs/{rid}/design/note.md").json()["content_text"] == "메모"


def test_vfs_put_base64_invalid_returns_400(client):
    """T17 가산 — 깨진 base64는 400."""
    rid = client.post("/runs", json={"title": "E"}).json()["run_id"]
    r = client.put(f"/vfs/{rid}/review/_render/ko.png", json={
        "content": "!!!not-base64!!!",
        "content_encoding": "base64",
        "mime": "image/png",
    })
    assert r.status_code == 400


def test_model_bound_provider_has_name_and_review_image():
    """_ModelBoundProvider 보강 회귀 — legal_search/vision 통합 위험 차단.

    legal_search.search_and_filter는 provider.name으로 model 인자를 구성하고,
    R1/R2 비전 호출은 review_image를 호출한다. 둘 다 _ModelBoundProvider에
    노출되어야 라이브 환경에서 AttributeError로 false live_unavailable 시그널이
    뜨지 않는다.
    """
    from app.server import create_app
    # create_app 내부에서 정의된 클래스를 직접 가져올 수 없으므로 동일 패턴으로
    # 구성 — 보강 의도가 코드에 반영됐는지 확인.
    create_app()  # smoke: 앱 빌드가 깨지지 않음
    import inspect
    from app import server as server_mod
    src = inspect.getsource(server_mod.create_app)
    assert "self.name = name" in src, "self.name 누락"
    assert "def review_image(" in src, "review_image pass-through 누락"


def test_cors_allows_configured_origin(monkeypatch):
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://foo.vercel.app")
    from app.server import create_app
    from fastapi.testclient import TestClient
    client = TestClient(create_app())
    r = client.options(
        "/health",
        headers={
            "Origin": "https://foo.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.headers.get("access-control-allow-origin") == "https://foo.vercel.app"


def test_cors_still_allows_localhost(monkeypatch):
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    from app.server import create_app
    from fastapi.testclient import TestClient
    client = TestClient(create_app())
    r = client.options(
        "/health",
        headers={"Origin": "http://localhost:3000",
                 "Access-Control-Request-Method": "GET"},
    )
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
