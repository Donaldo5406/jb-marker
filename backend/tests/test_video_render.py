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


def test_escape_drawtext_escapes_special_chars():
    from app.gateway.video.render import escape_drawtext
    out = escape_drawtext("a:b'c\\d")
    assert out == "a\\:b\\'c\\\\d"


def test_ff_color_hex_to_0x():
    from app.gateway.video.render import _ff_color
    assert _ff_color("#FFFFFF") == "0xFFFFFF"
    assert _ff_color("white") == "white"


def test_build_drawtext_filters_one_per_nonempty_layer():
    from app.gateway.video.render import build_drawtext_filters
    fs = build_drawtext_filters(STORY_OK, "ko", font_path="/f/Noto.ttc")
    assert len(fs) == 2                         # headline + disclosure
    head = fs[0]
    assert "drawtext=" in head and "fontfile='/f/Noto.ttc'" in head
    assert "text='높은 금리 적금'" in head
    assert ":fontsize=96" in head and ":fontcolor=0xFFFFFF" in head
    assert ":x=80:y=300" in head
    assert "enable='between(t,0.5,5.0)'" in head
    # disclosure 타이밍 8~12
    assert "enable='between(t,8.0,12.0)'" in fs[1]


def test_build_drawtext_filters_skips_missing_copy_and_omits_fontfile_when_none():
    from app.gateway.video.render import build_drawtext_filters
    story = json.loads(json.dumps(STORY_OK))
    story["copy"]["ko"].pop("disclosure")       # 문구 없음 → 스킵
    fs = build_drawtext_filters(story, "ko", font_path=None)
    assert len(fs) == 1
    assert "fontfile=" not in fs[0]             # 폰트 없으면 fontfile 생략(기본 폰트)
