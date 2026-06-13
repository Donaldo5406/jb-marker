"""video/scoring.py — 채점 + 타이밍(고지 노출시간) critic 결정론 검증."""
from app.gateway.video.scoring import (
    RUBRIC, DISCLOSURE_MIN_SEC, score_layout, evaluate_timing, timing_summary,
)


def _storyboard(disc_in, disc_out):
    return {"duration_sec": 15, "shots": [
        {"id": "s1", "start": 0.0, "end": 11.0, "layers": [
            {"role": "headline", "in": 0.5, "out": 3.8}]},
        {"id": "s2", "start": 11.0, "end": 15.0, "layers": [
            {"role": "disclosure", "in": disc_in, "out": disc_out}]}]}


def test_rubric_matches_design_seven_items():
    assert RUBRIC == ("hierarchy", "grid", "whitespace", "cta",
                      "compliance", "copy_visual", "brand")


def test_score_layout_pass_and_fail():
    assert score_layout({k: 5 for k in RUBRIC})["pass"] is True
    assert score_layout({k: 1 for k in RUBRIC})["pass"] is False


def test_timing_ok_when_disclosure_long_enough():
    sb = _storyboard(disc_in=11.0, disc_out=15.0)   # 4.0s >= 3.0
    assert evaluate_timing(sb) == []
    assert timing_summary(sb)["passed"] is True
    assert timing_summary(sb)["disclosure_sec"] == 4.0


def test_timing_violation_when_disclosure_too_short():
    sb = _storyboard(disc_in=14.0, disc_out=15.0)   # 1.0s < 3.0
    viols = evaluate_timing(sb)
    assert len(viols) == 1 and viols[0]["rule"] == "R-VID-DISCLOSURE-TIME"
    assert timing_summary(sb)["passed"] is False


def test_timing_violation_when_disclosure_missing():
    sb = {"duration_sec": 15, "shots": [
        {"id": "s1", "start": 0, "end": 15, "layers": [{"role": "headline"}]}]}
    viols = evaluate_timing(sb)
    assert len(viols) == 1 and viols[0]["rule"] == "R-VID-DISCLOSURE-TIME"
