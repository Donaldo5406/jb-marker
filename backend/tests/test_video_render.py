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


def _segs():
    from app.gateway.video.render import Segment
    return [Segment(kind="image", path="/t/s1.png", dur=6.0),
            Segment(kind="video", path="/t/s2.mp4", dur=6.0)]


def test_build_filter_complex_concat_and_drawtext_chain():
    from app.gateway.video.render import build_filter_complex
    fc = build_filter_complex(_segs(), ["drawtext=text='a'[x]REPLACED"], w=1080, h=1920, fps=30)
    # 세그먼트별 라벨 + concat + vout 산출
    assert "[0:v]scale=1080:1920" in fc and "crop=1080:1920" in fc
    assert "trim=duration=6.0" in fc               # video 세그먼트만 trim
    assert "concat=n=2:v=1:a=0[base]" in fc
    assert fc.strip().endswith("[vout]")


def test_build_filter_complex_no_drawtext_uses_null_passthrough():
    from app.gateway.video.render import build_filter_complex
    fc = build_filter_complex(_segs(), [], w=1080, h=1920, fps=30)
    assert "[base]null[vout]" in fc


def test_build_ffmpeg_command_inputs_map_and_music():
    from app.gateway.video.render import build_ffmpeg_command, build_drawtext_filters, Segment
    segs = [Segment(kind="image", path="/t/s1.png", dur=6.0),
            Segment(kind="color", path=None, dur=6.0, color="#0B2B5B")]
    dt = build_drawtext_filters(STORY_OK, "ko", font_path=None)
    argv = build_ffmpeg_command(segs, dt, out_path="/o/final.mp4",
                                w=1080, h=1920, fps=30, music_path="/m/bed.m4a")
    assert argv[0].endswith("ffmpeg") and "-y" in argv
    # image 세그먼트 → loop 입력
    assert "-loop" in argv and "/t/s1.png" in argv
    # color 세그먼트 → lavfi color 입력
    j = " ".join(argv)
    assert "lavfi" in j and "color=c=0x0B2B5B" in j
    # 음악 입력 + 맵 + shortest
    assert "-stream_loop" in argv and "/m/bed.m4a" in argv
    assert "-shortest" in argv and "[vout]" in argv
    assert argv[-1] == "/o/final.mp4"


def test_build_ffmpeg_command_without_music_has_no_audio_map():
    from app.gateway.video.render import build_ffmpeg_command, Segment
    argv = build_ffmpeg_command([Segment(kind="image", path="/t/s1.png", dur=6.0)],
                                [], out_path="/o/final.mp4", w=1080, h=1920, fps=30,
                                music_path=None)
    assert "-stream_loop" not in argv and "-shortest" not in argv
