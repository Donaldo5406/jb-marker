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


def test_breakdown_sums_to_excluded_and_is_policy_ordered(ledger, policies):
    """T10-UI: 사유 분해가 §50(정보통신망법)→§15·§16(개인정보보호법) 순으로,
    primary policy별 1회 집계 → count 합 = 제외 총수, reasons 합 = 정책 count."""
    out = build_eligibility(ledger, policies)
    bd = out["breakdown"]
    assert sum(g["count"] for g in bd) == len(out["excluded"])
    seen = [g["policy"] for g in bd]
    # 두 정책이 모두 있으면 infomatics가 pipa보다 앞.
    if "infomatics" in seen and "pipa" in seen:
        assert seen.index("infomatics") < seen.index("pipa")
    for g in bd:
        assert g["policy"] in {"infomatics", "pipa"}
        assert g["label"] and ("§50" in g["label"] or "§15" in g["label"])
        assert "law" in g["citation"]
        assert sum(r["count"] for r in g["reasons"]) == g["count"]
        assert all(r["label"] for r in g["reasons"])
