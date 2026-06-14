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
    assert "trim=duration=6.0" in fc               # 모든 세그먼트 trim+fps 정규화
    assert "fps=30" in fc                          # concat 전 fps 통일(image2 25fps 혼입 방지)
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


def _seed_footage(store, run_id, sid, content: bytes, mime: str):
    store.put(f"/{run_id}/video/design-system/components/footage/clip_{sid}.mp4",
              content, source="marker", mime=mime)


def test_render_video_fallback_writes_stub_when_no_ffmpeg(tmp_path):
    from app.gateway.video.render import render_video
    s = LocalVfsStore(storage_dir=str(tmp_path))
    _seed(s, "rv", STORY_OK)
    _seed_footage(s, "rv", "s1", b"\x89PNG\r\n\x1a\n", "image/png")
    # s2 footage 누락 → color 세그먼트 폴백
    path = render_video(s, "rv", lang="ko", ffmpeg=None)
    assert path == "/rv/review/_render/final.mp4"
    node = s.get(path)
    assert node is not None and node.blob is not None
    assert node.mime == "video/mp4"


def test_render_video_raises_compliance_before_touching_ffmpeg(tmp_path):
    from app.gateway.video.render import render_video, ComplianceError
    s = LocalVfsStore(storage_dir=str(tmp_path))
    _seed(s, "rv", _story_bad_disclosure())
    with pytest.raises(ComplianceError):
        render_video(s, "rv", lang="ko", ffmpeg=None)
    assert s.get("/rv/review/_render/final.mp4") is None   # 산출물 없음


def test_render_video_missing_storyboard_raises(tmp_path):
    from app.gateway.video.render import render_video, ComplianceError
    s = LocalVfsStore(storage_dir=str(tmp_path))
    s.create_run("rv", languages=["ko"])
    with pytest.raises(ComplianceError):
        render_video(s, "rv", lang="ko", ffmpeg=None)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg 미설치")
def test_render_video_real_ffmpeg_produces_nontrivial_mp4(tmp_path):
    from app.gateway.video.render import render_video, STUB_MP4
    s = LocalVfsStore(storage_dir=str(tmp_path))
    _seed(s, "rv", STORY_OK)
    _seed_footage(s, "rv", "s1", b"\x89PNG\r\n\x1a\n", "image/png")  # 깨진 PNG → color 폴백 경유
    path = render_video(s, "rv", lang="ko")   # auto-detect ffmpeg
    blob = s.get(path).blob
    assert blob is not None and len(blob) > len(STUB_MP4)


def _put_storyboard(client, run_id, story):
    # PUT /vfs 텍스트 노드(content_encoding 미지정) → store.put(path, content) 텍스트 저장.
    # 검증됨: routers/vfs.py PutText{content,mime,content_encoding}, get_text로 회수.
    return client.put(f"/vfs/{run_id}/video/storyboard/storyboard.spec.json",
                      json={"content": json.dumps(story), "mime": "application/json"})


def test_render_route_returns_422_on_noncompliant(local_client, monkeypatch):
    monkeypatch.setenv("MARKER_DISABLE_FFMPEG", "1")
    run_id = local_client.post("/runs", json={"title": "v"}).json()["run_id"]
    _put_storyboard(local_client, run_id, _story_bad_disclosure())
    r = local_client.post("/gateway/run", json={
        "run_id": run_id, "studio": "video", "prompt": "",
        "is_marker": True, "mock": True, "action": "render"})
    assert r.status_code == 422
    assert "고지" in r.json()["detail"]


def test_render_route_returns_200_and_render_path(local_client, monkeypatch):
    monkeypatch.setenv("MARKER_DISABLE_FFMPEG", "1")
    run_id = local_client.post("/runs", json={"title": "v"}).json()["run_id"]
    _put_storyboard(local_client, run_id, STORY_OK)
    r = local_client.post("/gateway/run", json={
        "run_id": run_id, "studio": "video", "prompt": "",
        "is_marker": True, "mock": True, "action": "render"})
    assert r.status_code == 200
    assert r.json()["output_path"] == f"/{run_id}/review/_render/final.mp4"


def test_build_segments_sniffs_image_bytes_despite_video_mime(tmp_path):
    from app.gateway.video.render import _build_segments
    import tempfile
    s = LocalVfsStore(storage_dir=str(tmp_path))
    s.create_run("rv", languages=["ko"])
    # demo/폴백 시나리오: PNG 바이트가 video/mp4로 오표기되어 저장됨(steps.V2aFootage)
    s.put("/rv/video/design-system/components/footage/clip_s1.mp4",
          b"\x89PNG\r\n\x1a\nxxxx", source="veo", mime="video/mp4")
    story = {"bg_color": "#000", "shots": [{"id": "s1", "start": 0, "end": 4, "layers": []}]}
    with tempfile.TemporaryDirectory() as td:
        segs = _build_segments(s, "rv", story, td, w=1080, h=1920)
    assert len(segs) == 1 and segs[0].kind == "image"   # mime이 video여도 PNG 매직 → image


def test_build_drawtext_filters_disables_expansion(tmp_path):
    from app.gateway.video.render import build_drawtext_filters
    story = {"shots": [{"layers": [{"role": "headline", "copy_key": "headline",
                                    "in": 0, "out": 3, "font_px": 80, "color": "#FFF",
                                    "bbox": {"x": 10, "y": 20}}]}],
             "copy": {"ko": {"headline": "연 3.5% 금리, 지금"}}}
    fs = build_drawtext_filters(story, "ko", font_path=None)
    assert "expansion=none" in fs[0]                 # '%' 리터럴화(치환·주입 방지)
    assert "3.5%" in fs[0]


def test_compliance_gate_raises_on_empty_disclosure_copy(tmp_path):
    from app.gateway.video.render import assert_render_compliance, ComplianceError
    story = json.loads(json.dumps(STORY_OK))
    story["copy"]["ko"]["disclosure"] = ""          # 타이밍은 OK(8~12=4s)지만 문구 빈칸
    with pytest.raises(ComplianceError) as ei:
        assert_render_compliance(story, "ko")
    assert "고지 문구" in str(ei.value)
