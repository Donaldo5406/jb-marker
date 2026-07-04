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
