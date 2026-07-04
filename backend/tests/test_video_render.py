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


def test_build_filter_complex_xfade_default_and_drawtext_chain():
    from app.gateway.video.render import build_filter_complex
    fc = build_filter_complex(_segs(), ["drawtext=text='a'[x]REPLACED"], w=1080, h=1920, fps=30)
    # 세그먼트별 정규화 + 기본 크로스페이드(joints=None→fade) + vout
    assert "[0:v]scale=1080:1920" in fc and "crop=1080:1920" in fc
    assert "trim=duration=6.0" in fc and "fps=30" in fc
    # seg0 길이 6, D=0.6 → offset=6-0.6=5.400, 마지막 조인트 출력=base
    assert "xfade=transition=fade:duration=0.6:offset=5.400[base]" in fc
    assert "concat=" not in fc                     # 기본은 크로스페이드(하드컷 아님)
    assert fc.strip().endswith("[vout]")


def test_build_filter_complex_cut_joint_uses_concat():
    from app.gateway.video.render import build_filter_complex
    fc = build_filter_complex(_segs(), [], w=1080, h=1920, fps=30, joints=["cut"])
    assert "concat=n=2:v=1:a=0[base]" in fc        # 'cut'=하드컷(concat)
    assert "xfade=" not in fc
    assert "[base]null[vout]" in fc


def test_build_filter_complex_single_segment_passthrough():
    from app.gateway.video.render import build_filter_complex, Segment
    fc = build_filter_complex([Segment("video", "/v.mp4", 6.0)], [],
                              w=1080, h=1920, fps=30)
    assert "[v0]null[base]" in fc and "[base]null[vout]" in fc  # 단일 샷=합성 없음
    assert "xfade=" not in fc and "concat=" not in fc


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
    import sys
    from app.gateway.video.render import render_video, STUB_MP4, _resolve_font
    # Windows ffmpeg는 drawtext fontfile의 드라이브 콜론(C:)을 못 읽는다(로컬 한정).
    font = _resolve_font()
    if sys.platform == "win32" and font and ":" in font:
        pytest.skip("Windows ffmpeg fontfile 드라이브 콜론 미지원(배포 Linux는 무관)")
    s = LocalVfsStore(storage_dir=str(tmp_path))
    _seed(s, "rv", STORY_OK)   # footage 미시드 → 두 샷 color 폴백(zoompan+grade+drawtext 실렌더)
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


# ── 시네마틱 빌더(순수 최적화) 회귀 ────────────────────────────────────────
def test_caption_deco_disclosure_box_others_shadow():
    from app.gateway.video.render import build_drawtext_filters
    fs = build_drawtext_filters(STORY_OK, "ko", font_path=None)
    head, disc = fs[0], fs[1]                         # headline, disclosure
    assert "shadowcolor=" in head and "borderw=2" in head and "box=1" not in head
    assert "box=1:boxcolor=black@" in disc           # 고지=박스 스크림(가독)


def test_drawtext_has_alpha_fade_ramp():
    from app.gateway.video.render import build_drawtext_filters
    fs = build_drawtext_filters(STORY_OK, "ko", font_path=None)
    assert ":alpha='max(0,min(1," in fs[0]           # 페이드 인/아웃 램프


def test_drawtext_rise_anim_makes_y_expression():
    from app.gateway.video.render import build_drawtext_filters
    story = json.loads(json.dumps(STORY_OK))
    story["shots"][0]["layers"][0]["anim"] = "rise-fade"
    fs = build_drawtext_filters(story, "ko", font_path=None)
    assert ":y='" in fs[0] and "max(0,1-(t-" in fs[0]   # 라이즈 이징식
    assert ":y=1700" in fs[1]                          # anim 없는 고지는 상수 y


def test_fontfile_opt_quotes_path():
    from app.gateway.video.render import _fontfile_opt
    assert _fontfile_opt("/f/Noto.ttc") == "fontfile='/f/Noto.ttc':"
    assert _fontfile_opt(None) == ""


def test_segment_chain_kenburns_on_stills_not_video_grade_on_all():
    from app.gateway.video.render import _segment_chain, Segment
    img = _segment_chain(0, Segment("image", "/i.png", 6.0), w=1080, h=1920, fps=30)
    col = _segment_chain(1, Segment("color", None, 6.0, "#000"), w=1080, h=1920, fps=30)
    vid = _segment_chain(2, Segment("video", "/v.mp4", 6.0), w=1080, h=1920, fps=30)
    assert "zoompan=" in img and "zoompan=" in col   # 정지/단색=켄번스
    assert "zoompan=" not in vid                      # 실 footage=이중무빙 회피
    for chain in (img, col, vid):                     # 그레이드는 전부 공통
        assert "eq=contrast=" in chain and "vignette=" in chain and "unsharp=" in chain


def test_dims_for_aspect_map():
    from app.gateway.video.render import _dims_for_aspect
    assert _dims_for_aspect("9:16") == (1080, 1920)
    assert _dims_for_aspect("16:9") == (1920, 1080)
    assert _dims_for_aspect("1:1") == (1080, 1080)
    assert _dims_for_aspect(None) == (1080, 1920)     # 기본 세로
    assert _dims_for_aspect("ugh") == (1080, 1920)    # 미지원 폴백


def test_music_filter_loudnorm_and_fades():
    from app.gateway.video.render import build_ffmpeg_command, Segment
    argv = build_ffmpeg_command([Segment("color", None, 6.0, "#000")], [],
                                out_path="/o.mp4", w=1080, h=1920, fps=30,
                                music_path="/m/bed.m4a")
    j = " ".join(argv)
    assert "loudnorm=" in j and "afade=t=in" in j and "afade=t=out" in j
    assert "[aout]" in argv and "-c:a" in argv


def test_x264_quality_tuning_flags():
    from app.gateway.video.render import build_ffmpeg_command, Segment
    argv = build_ffmpeg_command([Segment("color", None, 6.0, "#000")], [],
                                out_path="/o.mp4", w=1080, h=1920, fps=30, music_path=None)
    for flag in ("-crf", "18", "-preset", "slow", "-profile:v", "high", "+faststart"):
        assert flag in argv


# ── 크로스페이드 전환(정밀) ────────────────────────────────────────────────
def _segs3():
    from app.gateway.video.render import Segment
    return [Segment("video", "/a.mp4", 6.0), Segment("video", "/b.mp4", 6.0),
            Segment("video", "/c.mp4", 6.0)]


def test_joint_transition_resolution():
    from app.gateway.video.render import _joint_transition
    # right.transition_in 우선
    assert _joint_transition({"transition_out": "cut"}, {"transition_in": "fade"}) == "fade"
    # right 없으면 left.transition_out
    assert _joint_transition({"transition_out": "cut"}, {}) == "cut"
    # 미지정 기본 fade
    assert _joint_transition({}, {}) == "fade"
    # crossfade/dissolve 별칭 → fade, 미지원 → fade
    assert _joint_transition({}, {"transition_in": "crossfade"}) == "fade"
    assert _joint_transition({}, {"transition_in": "zoomwarp"}) == "fade"
    # 안전 화이트리스트는 유지
    assert _joint_transition({}, {"transition_in": "wipeleft"}) == "wipeleft"


def test_plan_transitions_offsets_and_total_all_fade():
    from app.gateway.video.render import plan_transitions
    story = {"shots": [{"transition_in": "fade"}, {"transition_in": "fade"},
                       {"transition_in": "fade"}]}
    plan = plan_transitions(story, _segs3())          # D=min(0.6, 6*0.5)=0.6
    assert plan["dur"] == 0.6
    assert plan["joints"] == ["fade", "fade"]
    # 샷별 누적 페이드 오프셋: 0, 0.6, 1.2
    assert plan["shot_offset"] == [0.0, 0.6, 1.2]
    # 총길이 = 18 - (2 페이드 * 0.6) = 16.8
    assert plan["total"] == 16.8


def test_plan_transitions_cut_joint_no_compression():
    from app.gateway.video.render import plan_transitions
    story = {"shots": [{}, {"transition_in": "cut"}, {"transition_in": "fade"}]}
    plan = plan_transitions(story, _segs3())
    assert plan["joints"] == ["cut", "fade"]
    # 첫 조인트 cut → 오프셋 누적 안 됨, 둘째 fade → +0.6
    assert plan["shot_offset"] == [0.0, 0.0, 0.6]
    assert plan["total"] == 18.0 - 0.6


def test_plan_transitions_clamps_dur_to_short_segment():
    from app.gateway.video.render import plan_transitions, Segment
    segs = [Segment("video", "/a.mp4", 0.8), Segment("video", "/b.mp4", 6.0)]
    plan = plan_transitions({"shots": [{}, {}]}, segs)   # D=min(0.6, 0.8*0.5=0.4)=0.4
    assert plan["dur"] == 0.4


def test_drawtext_shot_offsets_remap_preserve_duration():
    from app.gateway.video.render import build_drawtext_filters
    # 샷1(disclosure 8~12=4s)을 0.6 당겨도 노출 길이는 4s 보존 → 7.4~11.4
    fs = build_drawtext_filters(STORY_OK, "ko", font_path=None, shot_offsets=[0.0, 0.6])
    disc = fs[1]
    assert "between(t,7.4,11.4)" in disc
    # 길이 보존: 11.4-7.4 = 4.0 == 원본 12-8
    assert (11.4 - 7.4) == (12.0 - 8.0)
