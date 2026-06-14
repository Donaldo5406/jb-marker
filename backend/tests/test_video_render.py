"""video/render.py — 서버 렌더 서비스 단위/통합 (ffmpeg 없이 통과)."""
import json
import shutil

import pytest

from app.vfs.local import LocalVfsStore


STORY_OK = {
    "aspect": "9:16", "duration_sec": 12, "fps": 30, "bg_color": "#0B2B5B",
    "shots": [
        {"id": "s1", "start": 0.0, "end": 6.0,
         "layers": [
             {"role": "headline", "copy_key": "headline", "in": 0.5, "out": 5.0,
              "font_px": 96, "color": "#FFFFFF",
              "bbox": {"x": 80, "y": 300, "w": 900, "h": 220}}]},
        {"id": "s2", "start": 6.0, "end": 12.0,
         "layers": [
             {"role": "disclosure", "copy_key": "disclosure", "in": 8.0, "out": 12.0,
              "font_px": 36, "color": "#DDDDDD",
              "bbox": {"x": 60, "y": 1700, "w": 960, "h": 160}}]},
    ],
    "copy": {"ko": {"headline": "높은 금리 적금", "disclosure": "예금자보호법에 따라 보호"}},
    "audio": {"music": "uplifting", "voiceover": False},
}


def _story_bad_disclosure():
    s = json.loads(json.dumps(STORY_OK))
    s["shots"][1]["layers"][0]["out"] = 9.0   # 8.0~9.0 = 1.0s < 3.0s
    return s


def _seed(store, run_id, story):
    store.create_run(run_id, languages=["ko"])
    store.put(f"/{run_id}/video/storyboard/storyboard.spec.json",
              json.dumps(story), source="marker", mime="application/json")


def test_compliance_gate_raises_on_short_disclosure(tmp_path):
    from app.gateway.video.render import ComplianceError, assert_render_compliance
    with pytest.raises(ComplianceError) as ei:
        assert_render_compliance(_story_bad_disclosure())
    assert "고지" in str(ei.value)


def test_compliance_gate_passes_on_valid(tmp_path):
    from app.gateway.video.render import assert_render_compliance
    assert assert_render_compliance(STORY_OK) is None


def test_load_storyboard_reads_vfs(tmp_path):
    from app.gateway.video.render import load_storyboard
    s = LocalVfsStore(storage_dir=str(tmp_path))
    _seed(s, "rv", STORY_OK)
    sb = load_storyboard(s, "rv")
    assert sb["shots"][0]["id"] == "s1" and sb["copy"]["ko"]["headline"] == "높은 금리 적금"
