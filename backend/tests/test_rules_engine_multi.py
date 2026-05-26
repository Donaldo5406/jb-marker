"""다중 정책 합성 — §50 + §15·§16 합쳐서 가장 강한 BLOCK 채택."""
import pytest
from app.deploy.rules_engine import (
    load_policies, evaluate_recipient, evaluate_recipient_legacy,
    evaluate_infomatics,
)


@pytest.fixture
def policies():
    return load_policies()


def _r(**kw):
    base = {
        "id": "r1", "marketing_consent": True, "opt_out": False, "night_consent": True,
        "last_same_product_days": None, "lang": "ko",
        "collected_purpose": "marketing", "collected_days_ago": 10,
    }
    base.update(kw)
    return base


def test_both_allowed(policies):
    res = evaluate_recipient(_r(), send_hour=10, policies=policies)
    assert res["status"] == "ALLOWED"


def test_infomatics_block_pipa_allow(policies):
    res = evaluate_recipient(_r(opt_out=True), send_hour=10, policies=policies)
    assert res["status"] == "BLOCKED_OPT_OUT"
    assert res["policy"] == "infomatics"


def test_pipa_block_infomatics_allow(policies):
    res = evaluate_recipient(_r(collected_purpose="service"), send_hour=10, policies=policies)
    assert res["status"] == "BLOCKED_PURPOSE"
    assert res["policy"] == "pipa"


def test_both_block_priority_opt_out_wins(policies):
    """opt_out(0) < purpose(1) → opt_out이 채택, 둘 다 all_blocks에 기록."""
    res = evaluate_recipient(_r(opt_out=True, collected_purpose="service"), send_hour=10, policies=policies)
    assert res["status"] == "BLOCKED_OPT_OUT"
    statuses = {b["status"] for b in res["all_blocks"]}
    assert statuses == {"BLOCKED_OPT_OUT", "BLOCKED_PURPOSE"}


def test_legacy_wrapper_matches_infomatics_only(policies):
    """03 호환 wrapper = evaluate_infomatics 동일 결과."""
    r = _r(opt_out=True)
    expected = evaluate_infomatics(r, send_hour=10, policy=policies["infomatics"])
    actual = evaluate_recipient_legacy(r, 10, policies["infomatics"])
    assert actual["status"] == expected["status"]


def test_03_regression_night_blocked_no_consent(policies):
    """03 케이스 회귀: 야간(22시) + night_consent=False → BLOCKED_NIGHT."""
    res = evaluate_recipient_legacy(_r(night_consent=False), 22, policies["infomatics"])
    assert res["status"] == "BLOCKED_NIGHT"
