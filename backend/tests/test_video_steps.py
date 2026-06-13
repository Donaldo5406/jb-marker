"""video/steps.py — V0~V3 단위 검증 (design test_design_steps.py 패턴)."""
import json

from app.gateway.harness import HarnessRequest
from app.gateway.pipeline import StepContext
from app.providers.fake import FakeProvider
from app.vfs.local import LocalVfsStore


PLAN_MD = """---
medium: video
video_direction:
  duration_sec: 15
  aspect: "9:16"
  fps: 30
  pacing: medium
  palette: ["#0B2B5B", "#00857C"]
  font: Pretendard
footage_concept: 추상적 금융 성장 배경
scene_beats: [훅, 혜택, 신뢰, CTA]
copy_themes: [높은 금리, 신뢰]
languages: [ko]
factsheet:
  interest_rate: 3.5%
disclosures: [예금자보호법에 따라 5천만원까지 보호]
---
# 영상 계획
"""


def _store(tmp_path):
    s = LocalVfsStore(storage_dir=str(tmp_path))
    s.create_run("rv", languages=["ko"])
    s.put("/rv/brainstorming/plan.md", PLAN_MD, source="marker", mime="text/markdown")
    return s


def _ctx(store, provider, step="V0"):
    req = HarnessRequest(run_id="rv", studio="video", user_prompt="",
                         provider="fake", is_marker=True)
    return StepContext(req=req, provider=provider, store=store,
                       state={"step": step, "gate": None, "confirmed": {},
                              "bypass": {}, "languages": ["ko"]},
                       base="/rv/video")


def test_v0_setup_writes_tokens_and_matrix(tmp_path):
    from app.gateway.video.steps import V0Setup
    s = _store(tmp_path)
    ctx = _ctx(s, FakeProvider())
    V0Setup().run(ctx)
    tokens = json.loads(s.get("/rv/video/design-system/tokens.json").content_text)
    assert tokens["aspect"] == "9:16" and tokens["duration_sec"] == 15
    assert ctx.state["languages"] == ["ko"]


def test_v1_storyboard_writes_spec(tmp_path):
    from app.gateway.video.steps import V0Setup, V1Storyboard
    s = _store(tmp_path)
    ctx = _ctx(s, FakeProvider())
    V0Setup().run(ctx)
    # FakeProvider는 echo라 storyboard 키가 없음 → 빈 dict 저장(크래시 없이)
    V1Storyboard().run(ctx)
    node = s.get("/rv/video/storyboard/storyboard.spec.json")
    assert node is not None and json.loads(node.content_text) == {}


class _BoomVideo(FakeProvider):
    """generate_video가 항상 실패 → 폴백 경로 검증."""
    def generate_video(self, prompt, *, aspect="9:16", duration_sec=15, fps=30):
        raise RuntimeError("veo down")


def _seed_storyboard(store):
    sb = {"aspect": "9:16", "duration_sec": 15,
          "shots": [{"id": "s1", "footage_prompt": "추상 배경", "start": 0, "end": 15,
                     "layers": []}]}
    store.put("/rv/video/storyboard/storyboard.spec.json",
              json.dumps(sb), source="marker", mime="application/json")


def test_v2a_footage_generates_clip(tmp_path):
    from app.gateway.video.steps import V2aFootage
    s = _store(tmp_path)
    _seed_storyboard(s)
    res = V2aFootage(FakeProvider()).run(_ctx(s, FakeProvider(), step="V2a"))
    assert s.get("/rv/video/design-system/components/footage/clip_s1.mp4") is not None
    assert res.meta["footage_fallback"] is False


def test_v2a_footage_fallback_on_failure(tmp_path):
    from app.gateway.video.steps import V2aFootage
    s = _store(tmp_path)
    _seed_storyboard(s)
    res = V2aFootage(_BoomVideo()).run(_ctx(s, FakeProvider(), step="V2a"))
    assert s.get("/rv/video/design-system/components/footage/clip_s1.mp4") is not None
    assert res.meta["footage_fallback"] is True
