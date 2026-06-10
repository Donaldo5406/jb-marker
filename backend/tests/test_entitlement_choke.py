"""엔타이틀먼트 단일 choke — is_entitled(env override OR store) + 서버 경로 정합 (spec §7-1)."""
import json

from fastapi.testclient import TestClient


def test_is_entitled_env_override():
    from app import entitlement
    entitlement.set_override_source(lambda: True)
    try:
        assert entitlement.is_entitled("아무나") is True
    finally:
        entitlement.set_override_source(None)


def test_is_entitled_store_check():
    from app import entitlement
    entitlement.set_override_source(None)
    entitlement.reset()
    assert entitlement.is_entitled("u1") is False
    entitlement.set_dev_pass("u1")
    assert entitlement.is_entitled("u1") is True
    entitlement.reset()


def _client(monkeypatch, tmp_path, override: str | None):
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("JBM_STORAGE_DIR", str(tmp_path))
    if override is None:
        monkeypatch.delenv("ENTITLEMENT_OVERRIDE", raising=False)
    else:
        monkeypatch.setenv("ENTITLEMENT_OVERRIDE", override)
    from app.server import create_app
    return TestClient(create_app())


def _seed_package(c, rid):
    c.put(f"/vfs/{rid}/deploy/packages/sms_ko/copy.meta.json", json={
        "content": json.dumps({"original_text": "원본 카피", "disclosures": []},
                              ensure_ascii=False),
        "mime": "application/json"})


def test_advisor_respects_env_override(monkeypatch, tmp_path):
    """기존 불일치 회귀 가드: override=true면 advisor가 402를 내지 않는다."""
    c = _client(monkeypatch, tmp_path, "true")
    rid = c.post("/runs", json={"title": "t"}).json()["run_id"]
    _seed_package(c, rid)
    r = c.post(f"/runs/{rid}/deploy/advisor/chat",
               json={"package_id": "sms_ko", "message": "안녕", "mock": True})
    assert r.status_code != 402


def test_advisor_402_without_entitlement(monkeypatch, tmp_path):
    from app import entitlement
    c = _client(monkeypatch, tmp_path, None)
    entitlement.reset()   # create_app가 set_store로 store를 교체하므로 클라이언트 생성 '후' 정리
    rid = c.post("/runs", json={"title": "t"}).json()["run_id"]
    r = c.post(f"/runs/{rid}/deploy/advisor/chat",
               json={"package_id": "sms_ko", "message": "hi", "mock": True})
    assert r.status_code == 402


def test_dispatch_respects_env_override(monkeypatch, tmp_path):
    """dispatch도 동일 choke — override=true면 402가 아니라 다음 가드(400)로 진행."""
    c = _client(monkeypatch, tmp_path, "true")
    rid = c.post("/runs", json={"title": "t"}).json()["run_id"]
    r = c.post(f"/runs/{rid}/deploy/dispatch", json={"confirmed": True})
    # 수신자/채널 미준비라 400이 정상 — 402(entitlement)가 아니어야 한다.
    assert r.status_code == 400
