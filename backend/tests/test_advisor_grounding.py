"""advisor grounding 4 invariants."""
import pytest
from app.deploy.advisor.grounding import check


def test_pass_when_adapted_is_subset():
    original = "수익률 5% 보장 광고 수신거부"
    adapted = "수익률 5% 광고 수신거부 안내"  # "안내" = allowed paraphrase
    res = check(original, adapted, disclosures=["광고", "수신거부"])
    assert res.ok
    assert res.failures == []


def test_fail_on_unknown_token():
    original = "수익률 5%"
    adapted = "수익률 5% 무조건"  # "무조건" 신조어
    res = check(original, adapted, disclosures=[])
    assert not res.ok
    assert any("unknown_tokens" in f for f in res.failures)


def test_fail_on_number_mismatch():
    original = "수익률 5%"
    adapted = "수익률 6%"  # 숫자 변조
    res = check(original, adapted, disclosures=[])
    assert not res.ok
    assert any("number_mismatch" in f for f in res.failures)


def test_fail_on_missing_disclosure():
    original = "수익률 5% 광고 수신거부"
    adapted = "수익률 5%"  # 광고·수신거부 누락
    res = check(original, adapted, disclosures=["광고", "수신거부"])
    assert not res.ok
    assert any("missing_disclosures" in f for f in res.failures)


def test_allowed_paraphrase_does_not_fail():
    original = "혜택"
    adapted = "혜택 자세히 안내"  # 둘 다 allowed
    res = check(original, adapted, disclosures=[])
    assert res.ok


def test_multiple_failures_accumulate():
    original = "수익률 5%"
    adapted = "수익률 9% 무조건"
    res = check(original, adapted, disclosures=["광고"])
    assert not res.ok
    assert len(res.failures) >= 2  # number_mismatch + unknown_tokens + missing_disclosures
