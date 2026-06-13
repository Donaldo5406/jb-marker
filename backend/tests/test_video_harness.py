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
