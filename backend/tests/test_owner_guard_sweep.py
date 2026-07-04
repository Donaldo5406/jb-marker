"""run 소유권 가드 스위프 — run-scoped 전 라우트가 비소유자에게 404 (P4 T3 리뷰 후속).

T4~T6에서 핸들러가 라우터로 이동할 때 require_owner 호출이 누락되면
이 스위프가 잡는다. 새 run-scoped 라우트를 추가하면 ROUTES에 등록할 것.
"""
from fastapi.testclient import TestClient

from app.server import create_app


def _client_with_foreign_run(monkeypatch, tmp_path):
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("JBM_STORAGE_DIR", str(tmp_path))
    app = create_app()
    client = TestClient(app)
    app.state.store.create_run("foreign1", user_id="alice", title=None, languages=[])
    return client


# (method, path, json body) — run-scoped 전 라우트. body는 422를 피할 최소 형태.
ROUTES = [
    ("POST", "/gateway/run", {"run_id": "foreign1", "studio": "brainstorming", "prompt": "x"}),
    ("GET", "/runs/foreign1/session/design", None),
    ("POST", "/runs/foreign1/session/design/resume", None),
    ("POST", "/runs/foreign1/session/design/suspend", None),
    ("GET", "/runs/foreign1/sessions", None),
    ("GET", "/vfs/foreign1", None),
    ("GET", "/vfs/foreign1/brainstorming/spec.md", None),
    ("PUT", "/vfs/foreign1/x.md", {"content": "x"}),
    ("POST", "/runs/foreign1/deploy/setup", {"selected_providers": ["sms"], "languages": ["ko"]}),
    ("POST", "/runs/foreign1/deploy/eligibility", None),
    ("POST", "/runs/foreign1/deploy/packages",
     {"channel": "sms", "lang": "ko", "original_copy": "x", "visual_path": "/x"}),
    ("POST", "/runs/foreign1/deploy/advisor/chat", {"package_id": "sms_ko", "message": "x"}),
    ("GET", "/runs/foreign1/usage", None),
    ("GET", "/runs/foreign1/gallery", None),
    ("GET", "/runs/foreign1/preview", None),
    ("POST", "/runs/foreign1/deploy/dispatch", {"confirmed": True}),
    ("GET", "/runs/foreign1/deploy/_state", None),
]


def test_all_run_scoped_routes_hide_foreign_runs(monkeypatch, tmp_path):
    client = _client_with_foreign_run(monkeypatch, tmp_path)
    for method, path, body in ROUTES:
        r = client.request(method, path, json=body)
        assert r.status_code == 404, f"{method} {path} → {r.status_code} (404 기대)"
