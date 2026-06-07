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
        # citation 계약(프론트 EligibilityPanel이 의존): 객체 {law, article, source_url, quote},
        # source_url은 클릭 가능한 URL. (문자열 아님 — dict 렌더링 가정을 핀으로 고정)
        cit = g["citation"]
        assert isinstance(cit, dict), f"citation은 dict여야 함(프론트가 객체로 렌더): {cit!r}"
        assert cit["law"] and cit["article"]
        assert cit["source_url"].startswith("http")
        assert sum(r["count"] for r in g["reasons"]) == g["count"]
        assert all(r["label"] for r in g["reasons"])
