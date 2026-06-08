"""core/visual_rules — 시각 적법성 결정론 3룰 + WCAG 명도대비 계산 + 메타 보강."""
from app.core.visual_rules import (
    contrast_ratio,
    enrich_visual_metadata,
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


# --- FIX B: enrich_visual_metadata — font_px 미기재 시 bbox 높이로 보강 ---

def test_enrich_fills_font_px_from_bbox_dict():
    spec = {"slots": [
        {"role": "headline", "bbox": {"x": 0, "y": 0, "w": 900, "h": 120}},
        {"role": "disclosure", "bbox": {"h": 28}},
    ]}
    enrich_visual_metadata(spec)
    fonts = {s["role"]: s.get("font_px") for s in spec["slots"]}
    assert fonts["headline"] == 120 and fonts["disclosure"] == 28
    # 추정치 표식 — metadata가 측정값과 구분(다행 고지 과대추정 한계 명시용).
    assert all(s.get("font_px_estimated") is True for s in spec["slots"])


def test_summary_marks_estimated_font():
    spec = {"bg_color": "#FFF", "copy": {"ko": {"disclosure": "고지"}}, "slots": [
        {"role": "headline", "bbox": {"h": 100}, "color": "#000"},
        {"role": "disclosure", "bbox": {"h": 80}, "color": "#000"}]}
    enrich_visual_metadata(spec)
    assert visual_compliance_summary(spec)["font_px_estimated"] is True
    # 선언값(추정 아님) 스펙은 estimated=False.
    assert visual_compliance_summary(_spec())["font_px_estimated"] is False


def test_enrich_supports_bbox_list_form():
    spec = {"slots": [{"role": "body", "bbox": [10, 20, 400, 56]}]}
    enrich_visual_metadata(spec)
    assert spec["slots"][0]["font_px"] == 56


def test_enrich_preserves_existing_font_px():
    spec = {"slots": [{"role": "headline", "font_px": 72, "bbox": {"h": 999}}]}
    enrich_visual_metadata(spec)
    assert spec["slots"][0]["font_px"] == 72  # 기존값 유지(덮어쓰지 않음)
    assert "font_px_estimated" not in spec["slots"][0]  # 선언값엔 추정 표식 없음


def test_enrich_skips_when_no_bbox():
    spec = {"slots": [{"role": "headline"}]}
    enrich_visual_metadata(spec)
    assert "font_px" not in spec["slots"][0]


def test_enrich_makes_rvis1_effective_when_llm_omits_font():
    # 실 LLM이 font_px 없이 bbox만 준 경우 → 보강 후 R-VIS-1이 작은 고지를 잡는다.
    spec = {"bg_color": "#FFFFFF", "copy": {"ko": {"disclosure": "고지문"}}, "slots": [
        {"role": "headline", "bbox": {"h": 100}, "color": "#000000"},
        {"role": "disclosure", "bbox": {"h": 12}, "color": "#000000"},  # 12/100=12% < 30%
    ]}
    assert evaluate_visual_compliance(spec) == []  # 보강 전엔 font 룰 skip → 위반 없음
    enrich_visual_metadata(spec)
    fs = evaluate_visual_compliance(spec)
    assert any(f["rule"] == "R-VIS-1" for f in fs)
