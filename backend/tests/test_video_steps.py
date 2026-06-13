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


class _CopyProvider(FakeProvider):
    """V2b 카피 JSON을 반환(grounding 통과 카피)."""
    def complete(self, messages, *, model=None, system=None, tools=None, **kw):
        from app.providers.base import ProviderResponse
        return ProviderResponse(text=json.dumps({"copy": {"ko": {
            "headline": "연 3.5% 정기예금", "body": "지금 시작하세요.", "cta": "가입"}}}),
            model="x")


def test_v2b_copy_merges_into_storyboard(tmp_path):
    from app.gateway.video.steps import V2bCopy
    s = _store(tmp_path)
    _seed_storyboard(s)
    V2bCopy().run(_ctx(s, _CopyProvider(), step="V2b"))
    sb = json.loads(s.get("/rv/video/storyboard/storyboard.spec.json").content_text)
    assert sb["copy"]["ko"]["headline"] == "연 3.5% 정기예금"


def test_v2c_brand_attaches_disclosure(tmp_path):
    from app.gateway.video.steps import V2cBrand
    s = _store(tmp_path)
    _seed_storyboard(s)
    V2cBrand().run(_ctx(s, FakeProvider(), step="V2c"))
    sb = json.loads(s.get("/rv/video/storyboard/storyboard.spec.json").content_text)
    assert "disclosure" in sb["copy"]["ko"]
    assert "예금자보호" in sb["copy"]["ko"]["disclosure"]


def _seed_full_storyboard(store, disc_out=15.0):
    sb = {"aspect": "9:16", "duration_sec": 15, "shots": [
        {"id": "s1", "start": 0, "end": 11, "layers": [
            {"role": "headline", "in": 0.5, "out": 3.8}]},
        {"id": "s2", "start": 11, "end": 15, "layers": [
            {"role": "disclosure", "in": 11.0, "out": disc_out}]}],
        "copy": {"ko": {"headline": "연 3.5% 정기예금", "disclosure": "예금자보호 5천만원"}}}
    store.put("/rv/video/storyboard/storyboard.spec.json",
              json.dumps(sb), source="marker", mime="application/json")


def test_v3_final_writes_metadata_and_caches_critic(tmp_path):
    from app.gateway.video.steps import V3Final, V3_CRITIC_CACHE
    s = _store(tmp_path)
    _seed_full_storyboard(s)
    ctx = _ctx(s, FakeProvider(), step="V3")
    res = V3Final().run(ctx)
    md = s.get("/rv/video/metadata.md").content_text
    assert "타이밍 적법성" in md and "disclosure_sec" in md
    assert V3_CRITIC_CACHE in ctx.cache
    assert res.meta["critic"]["passed"] in (True, False)


def test_step_declarations_derive_constants():
    from app.gateway.video.steps import (
        STEP_CLASSES, STEPS, GATED_STEPS, CRITIC_STEPS)
    assert STEPS == tuple(c.name for c in STEP_CLASSES) + ("done",)
    assert STEPS == ("V0", "V1", "V2a", "V2b", "V2c", "V3", "done")
    assert GATED_STEPS == ("V1", "V2a", "V2b", "V2c", "V3")
    assert CRITIC_STEPS == ("V1", "V3")


def test_demo_provider_routes_video_v1():
    from app.providers.demo import DemoProvider
    from app.gateway.prompt import PromptSpec
    p = DemoProvider()
    pspec = PromptSpec(persona="x", studio="video", step="V1")
    resp = p.complete([], system=pspec.assemble(), meta=pspec.meta)
    assert "storyboard" in resp.text   # V1 fixture JSON
