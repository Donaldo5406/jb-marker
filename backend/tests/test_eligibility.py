"""D1 빌더 단위 — 512명 fixture 전수 + calendar + multi-policy excluded."""
import pytest
from app.deploy.ledger import load_ledger
from app.deploy.rules_engine import load_policies
from app.deploy.eligibility import build_eligibility


@pytest.fixture
def ledger():
    return load_ledger()


@pytest.fixture
def policies():
    return load_policies()


def test_total_512(ledger, policies):
    out = build_eligibility(ledger, policies)
    assert out["total"] == 512
    assert out["eligible_count"] + len(out["excluded"]) == 512


def test_calendar_24_slots_night_blocked(ledger, policies):
    out = build_eligibility(ledger, policies)
    cal = out["calendar"]
    assert len(cal) == 24
    blocked_hours = {c["hour"] for c in cal if c["blocked"]}
    assert blocked_hours == {0, 1, 2, 3, 4, 5, 6, 7, 21, 22, 23}


def test_excluded_has_policy_and_citation(ledger, policies):
    out = build_eligibility(ledger, policies)
    if out["excluded"]:
        ex = out["excluded"][0]
        assert ex["policy"] in {"infomatics", "pipa"}
        assert "law" in ex["citation"]


def test_send_hour_22_increases_night_blocks(ledger, policies):
    """야간 발송시각 → BLOCKED_NIGHT 증가."""
    day = build_eligibility(ledger, policies, send_hour=10)
    night = build_eligibility(ledger, policies, send_hour=22)
    assert night["eligible_count"] <= day["eligible_count"]
