"""M6 골든 패스 통합 — D0→D1→D2→D3→report."""
import json
import pytest
from fastapi.testclient import TestClient
from app.server import app
from app import entitlement


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_ent():
    entitlement.reset()
    yield
    entitlement.reset()


def test_golden_path_end_to_end(client):
    # 0. run 생성
    r = client.post("/runs", json={"languages": ["ko", "vi"]})
    rid = r.json()["run_id"]

    # 1. D0 setup
    s = client.post(f"/runs/{rid}/deploy/setup", json={"selected_providers": ["email"], "languages": ["ko"]})
    assert s.status_code == 200
    assert len(s.json()["matrix"]) == 1

    # 2. D1 eligibility
    e = client.post(f"/runs/{rid}/deploy/eligibility")
    assert e.json()["total"] == 512

    # 3. D2 package (within limits)
    p = client.post(f"/runs/{rid}/deploy/packages", json={
        "channel": "email", "lang": "ko", "original_copy": "수익률 5% 광고 수신거부", "visual_path": "/x.png",
    })
    assert p.json()["status"] == "ok"

    # 4. dispatch w/o entitlement = 402 (게이트 유지 — 결제 표면만 폐기, spec 2026-07-04)
    client.app.state.store.set_step_status(rid, "review", "PASS")
    d_fail = client.post(f"/runs/{rid}/deploy/dispatch", json={"confirmed": True})
    assert d_fail.status_code == 402

    # 5. entitlement 직접 부여(demo-payment 엔드포인트는 폐기됨)
    entitlement.set_dev_pass("demo")

    # 6. dispatch happy
    d_ok = client.post(f"/runs/{rid}/deploy/dispatch", json={"confirmed": True})
    assert d_ok.status_code == 200
    assert d_ok.json()["step_status"] == "PASS"

    # 7. state 확인
    st = client.get(f"/runs/{rid}/deploy/_state")
    assert st.json()["step_status"] == "PASS"
