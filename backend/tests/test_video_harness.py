"""VideoHarness 셸 — 오케스트레이터 동기·done·state (test_design_steps 패턴)."""
from app.gateway.harness_video import VideoHarness
from app.gateway.video.steps import STEPS
from app.providers.fake import FakeProvider


def test_orchestrator_synced_to_step_declarations():
    h = VideoHarness(video_provider=FakeProvider())
    assert h._orch.step_names == STEPS
    assert h._orch.studio == "video"


def test_load_state_default_v0():
    from app.vfs.local import LocalVfsStore
    s = LocalVfsStore(); s.create_run("rv2")
    h = VideoHarness(video_provider=FakeProvider())
    st = h._load_state(s, "rv2")
    assert st["step"] == "V0" and st["gate"] is None and st["languages"] == ["ko"]


def test_render_action_dispatches_to_render_video(tmp_path, monkeypatch):
    import json
    from app.gateway.harness_video import VideoHarness
    from app.gateway.harness import HarnessRequest
    from app.vfs.local import LocalVfsStore

    s = LocalVfsStore(storage_dir=str(tmp_path))
    s.create_run("rv3", languages=["ko"])
    story = {"aspect": "9:16", "fps": 30, "bg_color": "#0B2B5B",
             "shots": [{"id": "s1", "start": 0.0, "end": 6.0,
                        "layers": [{"role": "disclosure", "copy_key": "disclosure",
                                    "in": 0.0, "out": 6.0, "font_px": 36,
                                    "color": "#FFF", "bbox": {"x": 0, "y": 0}}]}],
             "copy": {"ko": {"disclosure": "보호"}}}
    s.put("/rv3/video/storyboard/storyboard.spec.json", json.dumps(story),
          source="marker", mime="application/json")

    h = VideoHarness(video_provider=FakeProvider())
    req = HarnessRequest(run_id="rv3", studio="video", user_prompt="",
                         provider="fake", is_marker=True, action="render")
    # ffmpeg 의존 제거 — env로 강제 stub
    monkeypatch.setenv("MARKER_DISABLE_FFMPEG", "1")
    res = h.handle_turn(req, provider=FakeProvider(), store=s)

    assert res.output_path == "/rv3/review/_render/final.mp4"
    assert any(ev.get("type") == "artifact"
               and ev.get("path") == "/rv3/review/_render/final.mp4"
               for ev in res.events)
    assert s.get("/rv3/review/_render/final.mp4") is not None


def test_render_stub_warns_in_live_but_not_mock(tmp_path, monkeypatch):
    """A2 폴백 가시화: stub 폴백을 라이브에선 정직히 경고, Mock(의도된 stub)은 오경보 안 함."""
    import json
    from app.gateway.harness import HarnessRequest
    from app.vfs.local import LocalVfsStore

    s = LocalVfsStore(storage_dir=str(tmp_path))
    story = {"aspect": "9:16", "fps": 30, "bg_color": "#0B2B5B",
             "shots": [{"id": "s1", "start": 0.0, "end": 6.0,
                        "layers": [{"role": "disclosure", "copy_key": "disclosure",
                                    "in": 0.0, "out": 6.0, "font_px": 36,
                                    "color": "#FFF", "bbox": {"x": 0, "y": 0}}]}],
             "copy": {"ko": {"disclosure": "보호"}}}
    for run in ("live", "demo"):
        s.create_run(run, languages=["ko"])
        s.put(f"/{run}/video/storyboard/storyboard.spec.json", json.dumps(story),
              source="marker", mime="application/json")
    monkeypatch.setenv("MARKER_DISABLE_FFMPEG", "1")   # 강제 stub
    h = VideoHarness(video_provider=FakeProvider())

    # 라이브(mock=False) + stub → 정직한 경고 + meta.render=stub
    live = h.handle_turn(
        HarnessRequest(run_id="live", studio="video", user_prompt="", provider="fake",
                       is_marker=True, action="render", mock=False),
        provider=FakeProvider(), store=s)
    assert "임시 파일" in live.text and live.meta["render"] == "stub"

    # Mock(데모) + stub → 의도된 결정론 산출, 오경보 없음
    demo = h.handle_turn(
        HarnessRequest(run_id="demo", studio="video", user_prompt="", provider="fake",
                       is_marker=True, action="render", mock=True),
        provider=FakeProvider(), store=s)
    assert "렌더했습니다" in demo.text


def test_render_action_compliance_violation_propagates(tmp_path, monkeypatch):
    import json
    import pytest
    from app.gateway.harness_video import VideoHarness
    from app.gateway.harness import HarnessRequest
    from app.gateway.video.render import ComplianceError
    from app.vfs.local import LocalVfsStore

    s = LocalVfsStore(storage_dir=str(tmp_path))
    s.create_run("rv4", languages=["ko"])
    story = {"aspect": "9:16", "fps": 30, "shots": [], "copy": {"ko": {}}}  # disclosure 없음
    s.put("/rv4/video/storyboard/storyboard.spec.json", json.dumps(story),
          source="marker", mime="application/json")
    h = VideoHarness(video_provider=FakeProvider())
    req = HarnessRequest(run_id="rv4", studio="video", user_prompt="",
                         provider="fake", is_marker=True, action="render")
    monkeypatch.setenv("MARKER_DISABLE_FFMPEG", "1")
    with pytest.raises(ComplianceError):
        h.handle_turn(req, provider=FakeProvider(), store=s)
