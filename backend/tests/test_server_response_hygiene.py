"""HTTP/WS 표면 위생 — 내부 키(_usage/_model) 비노출 + WS 이벤트 type 키 통일 (spec §7-7·§8.2)."""
import json

from fastapi.testclient import TestClient


def _client(monkeypatch, tmp_path):
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("JBM_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "true")
    from app.server import create_app
    return TestClient(create_app())


def test_advisor_response_has_no_internal_underscore_keys(monkeypatch, tmp_path):
    c = _client(monkeypatch, tmp_path)
    rid = c.post("/runs", json={"title": "t"}).json()["run_id"]
    c.put(f"/vfs/{rid}/deploy/packages/sms_ko/copy.meta.json", json={
        "content": json.dumps({"original_text": "원본 카피", "disclosures": []},
                              ensure_ascii=False),
        "mime": "application/json"})
    r = c.post(f"/runs/{rid}/deploy/advisor/chat",
               json={"package_id": "sms_ko", "message": "짧게 압축해줘", "mock": True})
    assert r.status_code == 200
    body = r.json()
    assert "_usage" not in body and "_model" not in body


def test_ws_restored_event_uses_type_key():
    """server.py의 restored publish dict가 type 키 체계를 따른다 — 소스 레벨 가드.

    (WS 통합 재현은 세션 suspend 타이밍 의존이라 소스 단언으로 회귀를 막는다.
    이벤트 스키마의 단일 문서화는 P5 ws_protocol.md.)
    """
    import inspect
    import app.server as server_mod
    src = inspect.getsource(server_mod)
    assert '{"kind": "restored"' not in src
    assert '"type": "session"' in src
