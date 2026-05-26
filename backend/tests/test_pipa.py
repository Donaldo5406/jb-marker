"""pipa(개인정보보호법 §15·§16) 평가 단위."""
import pytest
from app.deploy.rules_engine import load_policies, evaluate_pipa


@pytest.fixture
def pipa():
    return load_policies()["pipa"]


def test_purpose_violation_blocks(pipa):
    r = {"id": "x1", "collected_purpose": "service", "collected_days_ago": 10}
    res = evaluate_pipa(r, pipa)
    assert res["status"] == "BLOCKED_PURPOSE"
    assert "제15조" in res["citation"]["article"]


def test_retention_expired_blocks(pipa):
    r = {"id": "x2", "collected_purpose": "marketing", "collected_days_ago": 1000}
    res = evaluate_pipa(r, pipa)
    assert res["status"] == "BLOCKED_RETENTION"
    assert "제16조" in res["citation"]["article"]


def test_purpose_ok_and_within_retention_allowed(pipa):
    r = {"id": "x3", "collected_purpose": "marketing", "collected_days_ago": 100}
    res = evaluate_pipa(r, pipa)
    assert res["status"] == "ALLOWED"
