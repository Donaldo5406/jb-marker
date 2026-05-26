"""severity 모듈 단위 — 게이트 산정·WARN 강등·키워드 안전망."""
import pytest

from app.core.severity import (
    compute_gate, EXAGGERATION_TOKENS, DISCLOSURE_I18N,
    detect_exaggeration, find_missing_disclosures,
)


def _v(severity, **kw):
    return {"severity": severity, **kw}


def test_gate_pass_no_findings():
    g = compute_gate([], flags={})
    assert g == {"status": "PASS", "critical_count": 0, "warning_count": 0}


def test_gate_warn_only():
    g = compute_gate([_v("warning"), _v("warning")], flags={})
    assert g["status"] == "WARN"
    assert g["warning_count"] == 2 and g["critical_count"] == 0


def test_gate_blocked_any_critical():
    g = compute_gate([_v("critical"), _v("warning")], flags={})
    assert g["status"] == "BLOCKED"
    assert g["critical_count"] == 1


@pytest.mark.parametrize("flag", [
    {"live_unavailable": True},
    {"parse_failed": True},
    {"vision_failed": True},
    {"step_failed": "R1"},
    {"vision_skipped": ["visual/v1.png"]},
])
def test_gate_pass_demoted_to_warn_by_flags(flag):
    """5트리거 어느 하나라도 → PASS 산정이어도 WARN으로 강등(spec §7.3)."""
    g = compute_gate([], flags=flag)
    assert g["status"] == "WARN"


def test_gate_blocked_not_demoted_by_flags():
    """BLOCKED은 강등 트리거와 무관하게 BLOCKED 유지."""
    g = compute_gate([_v("critical")], flags={"live_unavailable": True})
    assert g["status"] == "BLOCKED"


def test_detect_exaggeration_vi():
    assert detect_exaggeration("Sản phẩm tốt nhất, chắc chắn sinh lời.")
    assert not detect_exaggeration("Đây là sản phẩm tài chính.")


def test_detect_exaggeration_zh():
    assert detect_exaggeration("保证盈利, 零风险")
    assert not detect_exaggeration("普通描述")


def test_find_missing_disclosures_vi():
    body = "Đây là sản phẩm."
    missing = find_missing_disclosures(body, "vi", ["미래 수익 보장 아님"])
    assert missing == ["미래 수익 보장 아님"]


def test_find_missing_disclosures_found():
    body = "lãi suất trước thuế áp dụng."
    missing = find_missing_disclosures(body, "vi", ["세전 금리, 우대조건 충족 시"])
    assert missing == []


def test_disclosure_i18n_mapping_exists():
    """03 키워드 매핑이 이식되어 있어야 함."""
    assert "미래 수익 보장 아님" in DISCLOSURE_I18N
    assert "vi" in DISCLOSURE_I18N["미래 수익 보장 아님"]
