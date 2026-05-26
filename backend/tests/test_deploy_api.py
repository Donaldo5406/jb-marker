"""7개 deploy 라우트 happy + entitlement 402."""
import json

import pytest
from fastapi.testclient import TestClient

from app import entitlement
from app.server import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.fixture
def run_id(client):
    """M5 PASS 상태인 run 생성 — TODO 통합 시 review 게이트 우회 fixture."""
    res = client.post("/runs", json={"title": "deploy-test", "languages": ["ko", "vi"]})
    assert res.status_code == 200
    return res.json()["run_id"]


@pytest.fixture(autouse=True)
def _reset_entitlement():
    entitlement.reset()
    yield
    entitlement.reset()


# ----- Task 12: setup -----------------------------------------------------

def test_setup_produces_matrix(client, run_id):
    res = client.post(
        f"/runs/{run_id}/deploy/setup",
        json={"selected_providers": ["email", "kakao"], "languages": ["ko", "vi"]},
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body["matrix"]) == 4
    assert body["step_status"] == "in_progress"


# ----- Task 13: eligibility -----------------------------------------------

def test_eligibility_returns_counts(client, run_id):
    res = client.post(f"/runs/{run_id}/deploy/eligibility")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 512
    assert body["eligible_count"] + body["excluded_count"] == 512


# ----- Task 14: packages --------------------------------------------------

def test_packages_within_limits_ok(client, run_id):
    res = client.post(
        f"/runs/{run_id}/deploy/packages",
        json={"channel": "email", "lang": "ko", "original_copy": "짧은 카피", "visual_path": "/x.png"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_packages_over_limits_needs_advisor(client, run_id):
    res = client.post(
        f"/runs/{run_id}/deploy/packages",
        json={"channel": "sms", "lang": "ko", "original_copy": "x" * 200, "visual_path": "/x.png"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "needs_advisor"


# ----- Task 15: advisor chat ----------------------------------------------

def test_advisor_chat_blocked_without_dev_pass(client, run_id):
    entitlement.reset()
    res = client.post(
        f"/runs/{run_id}/deploy/advisor/chat",
        json={"package_id": "email_ko", "message": "압축해줘"},
    )
    assert res.status_code == 402


def test_advisor_chat_passes_with_dev_pass(client, run_id):
    entitlement.set_dev_pass("demo")
    # 패키지 seed 먼저
    client.post(
        f"/runs/{run_id}/deploy/packages",
        json={"channel": "sms", "lang": "ko", "original_copy": "수익률 5%" * 30, "visual_path": "/x.png"},
    )
    res = client.post(
        f"/runs/{run_id}/deploy/advisor/chat",
        json={"package_id": "sms_ko", "message": "압축해줘"},
    )
    assert res.status_code == 200


# ----- Task 16: dispatch --------------------------------------------------

def test_dispatch_requires_confirm(client, run_id):
    entitlement.set_dev_pass("demo")
    res = client.post(f"/runs/{run_id}/deploy/dispatch", json={"confirmed": False})
    assert res.status_code == 400


def test_dispatch_requires_dev_pass(client, run_id):
    entitlement.reset()
    res = client.post(f"/runs/{run_id}/deploy/dispatch", json={"confirmed": True})
    assert res.status_code == 402


def test_dispatch_happy_writes_report(client, run_id):
    entitlement.set_dev_pass("demo")
    client.post(
        f"/runs/{run_id}/deploy/setup",
        json={"selected_providers": ["email"], "languages": ["ko"]},
    )
    client.post(f"/runs/{run_id}/deploy/eligibility")
    client.post(
        f"/runs/{run_id}/deploy/packages",
        json={"channel": "email", "lang": "ko", "original_copy": "짧은 카피", "visual_path": "/x.png"},
    )
    res = client.post(f"/runs/{run_id}/deploy/dispatch", json={"confirmed": True})
    assert res.status_code == 200
    assert res.json()["step_status"] == "PASS"


# ----- Task 17: demo-payment + _state -------------------------------------

def test_demo_payment_sets_dev_pass(client, run_id):
    entitlement.reset()
    res = client.post(f"/runs/{run_id}/deploy/demo-payment")
    assert res.status_code == 200
    assert res.json()["dev_pass"] is True
    assert entitlement.check("demo") is True


def test_state_reflects_setup(client, run_id):
    client.post(
        f"/runs/{run_id}/deploy/setup",
        json={"selected_providers": ["email"], "languages": ["ko"]},
    )
    res = client.get(f"/runs/{run_id}/deploy/_state")
    body = res.json()
    assert body["selected_providers"] == ["email"]
    assert body["step_status"] == "in_progress"
