# backend/tests/test_review_highlight.py
from app.gateway.review_highlight import (
    canvas_of, slot_to_bbox_norm, reviewed_image_for, clamp01,
)

LAYOUT = {
    "slots": [
        {"role": "background", "bbox": {"x": 0, "y": 0, "w": 1080, "h": 1350}},
        {"role": "headline", "bbox": {"x": 80, "y": 160, "w": 920, "h": 200}},
        {"role": "disclosure", "bbox": {"x": 80, "y": 1276, "w": 920, "h": 58}},
    ]
}

def test_canvas_of_reads_background_slot():
    assert canvas_of(LAYOUT) == (1080, 1350)

def test_canvas_of_defaults_when_missing():
    assert canvas_of({"slots": []}) == (1080, 1350)

def test_slot_to_bbox_norm_headline():
    b = slot_to_bbox_norm("headline", LAYOUT)
    assert b == {"x": 80/1080, "y": 160/1350, "w": 920/1080, "h": 200/1350}

def test_slot_to_bbox_norm_unknown_slot_is_none():
    assert slot_to_bbox_norm("nope", LAYOUT) is None

def test_reviewed_image_for_scene_maps_to_baked_visual():
    assert reviewed_image_for("design/final/ko/main.scene", "ko") == \
        "design/design-system/components/visual/v1.png"

def test_reviewed_image_for_png_passthrough():
    assert reviewed_image_for("review/uploads/poster.png", None) == \
        "review/uploads/poster.png"

def test_clamp01():
    assert clamp01(-0.2) == 0.0 and clamp01(1.4) == 1.0 and clamp01(0.5) == 0.5


from app.gateway.review_highlight import build_highlight_html

def _rects():
    return [
        {"x": 0.074, "y": 0.118, "w": 0.5, "h": 0.15, "severity": "critical", "pin": 1},
        {"x": 0.074, "y": 0.945, "w": 0.85, "h": 0.043, "severity": "warning", "pin": 2, "label": "고지"},
    ]

def test_build_html_is_self_contained_data_uri():
    out = build_highlight_html(b"\x89PNG\r\n", "image/png", _rects())
    assert out.startswith("<!doctype html>")
    assert "data:image/png;base64," in out
    # 외부 리소스 금지(네트워크 요청 0)
    assert "http://" not in out and "https://" not in out

def test_build_html_places_each_rect_percent():
    out = build_highlight_html(b"x", "image/png", _rects())
    assert "left:7.4%" in out and "top:11.8%" in out and "width:50%" in out
    assert "class=\"hl crit\"" in out and "class=\"hl warn\"" in out

def test_build_html_renders_pins():
    out = build_highlight_html(b"x", "image/png", _rects())
    assert ">1<" in out and ">2<" in out

def test_build_html_empty_rects_shows_image_only():
    out = build_highlight_html(b"x", "image/png", [])
    assert "class=\"hl" not in out and "data:image/png;base64," in out
