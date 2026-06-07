"""core/visual_rules — 시각 적법성 결정론 3룰 + WCAG 명도대비 계산."""
from app.core.visual_rules import (
    contrast_ratio,
    evaluate_visual_compliance,
    visual_compliance_summary,
)


def _spec(disc_font=26, disc_color="#3A3A3A", bg="#F2EFE9", head_font=72,
          disclosure_slot=True, disc_copy="예금자보호법에 따라 5천만원까지 보호"):
    slots = [
        {"role": "headline", "font_px": head_font, "color": "#0B1324"},
        {"role": "body", "font_px": 34, "color": "#1A2332"},
    ]
    if disclosure_slot:
        slots.append({"role": "disclosure", "font_px": disc_font, "color": disc_color})
    copy = {"ko": {"disclosure": disc_copy}} if disc_copy else {"ko": {}}
    return {"bg_color": bg, "slots": slots, "copy": copy}


def test_compliant_spec_has_no_findings():
    assert evaluate_visual_compliance(_spec()) == []


def test_missing_disclosure_slot_is_critical():
    fs = evaluate_visual_compliance(_spec(disclosure_slot=False))
    assert len(fs) == 1 and fs[0]["rule"] == "R-VIS-3" and fs[0]["severity"] == "critical"


def test_empty_disclosure_copy_is_critical():
    fs = evaluate_visual_compliance(_spec(disc_copy=""))
    assert any(f["rule"] == "R-VIS-3" and f["severity"] == "critical" for f in fs)


def test_small_disclosure_font_is_warning():
    fs = evaluate_visual_compliance(_spec(disc_font=10))  # 10/72 = 0.14 < 0.3
    rule1 = [f for f in fs if f["rule"] == "R-VIS-1"]
    assert rule1 and rule1[0]["severity"] == "warning"
    assert rule1[0]["official_source_url"].startswith("http")


def test_low_contrast_is_warning():
    fs = evaluate_visual_compliance(_spec(disc_color="#EEEEEE"))  # 밝은 회색/밝은 배경
    assert any(f["rule"] == "R-VIS-2" and f["severity"] == "warning" for f in fs)


def test_contrast_ratio_black_on_white_is_21():
    assert contrast_ratio("#000000", "#FFFFFF") == 21.0


def test_contrast_ratio_bad_hex_returns_none():
    assert contrast_ratio("nope", "#FFFFFF") is None
    assert contrast_ratio("#FFFFFF", None) is None


def test_missing_metadata_skips_font_and_contrast_rules():
    # font_px/color 없는 슬롯 → R-VIS-1/2 graceful skip, 고지 존재(R-VIS-3)만 평가 → 위반 없음.
    spec = {"slots": [{"role": "headline"}, {"role": "disclosure"}],
            "copy": {"ko": {"disclosure": "고지"}}}
    assert evaluate_visual_compliance(spec) == []


def test_summary_reports_metrics_and_pass():
    s = visual_compliance_summary(_spec())
    assert s["passed"] is True
    assert s["disclosure_font_px"] == 26 and s["max_text_font_px"] == 72
    assert s["disclosure_contrast"] is not None and s["disclosure_contrast"] >= 4.5


def test_summary_reports_violations():
    s = visual_compliance_summary(_spec(disc_font=10))
    assert s["passed"] is False
    assert any(v["rule"] == "R-VIS-1" for v in s["violations"])
