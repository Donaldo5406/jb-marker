"""Video 파이프라인 e2e — VideoHarness + DemoProvider로 V0→done 완주(통합 회귀 잠금).

demo fixtures(VIDEO_PLAN_MD·STORYBOARD_SPEC)의 커밋된 소비자 — plan(medium=video)을
VideoHarness가 소비해 토큰·콘티·footage·metadata를 산출하고 타이밍 적법성을 통과하는지 확인.
"""
import json

from app.gateway.harness import HarnessRequest
from app.gateway.harness_video import VideoHarness
from app.providers import demo_fixtures as F
from app.providers.demo import DemoProvider
from app.vfs.local import LocalVfsStore


def _run_to_done(h, demo, store, run_id):
    req = HarnessRequest(run_id=run_id, studio="video", user_prompt="영상 시작",
                         provider="demo", is_marker=True,
                         bypass_map={s: True for s in ("V1", "V2a", "V2b", "V2c", "V3")})
    res = h.handle_turn(req, provider=demo, store=store)
    for _ in range(10):
        if res.meta.get("step") == "done":
            break
        req2 = HarnessRequest(run_id=run_id, studio="video", user_prompt="",
                              provider="demo", is_marker=True, action="advance")
        res = h.handle_turn(req2, provider=demo, store=store)
    return res


def test_video_pipeline_demo_runs_to_done_and_passes_timing(tmp_path):
    store = LocalVfsStore(storage_dir=str(tmp_path))
    store.create_run("vid_e2e", languages=["ko", "en", "vi", "zh"])
    store.put("/vid_e2e/brainstorming/plan.md", F.VIDEO_PLAN_MD,
              source="marker", mime="text/markdown")
    demo = DemoProvider()
    h = VideoHarness(video_provider=demo)
    res = _run_to_done(h, demo, store, "vid_e2e")

    assert res.meta.get("step") == "done"
    for p in ["/vid_e2e/video/design-system/tokens.json",
              "/vid_e2e/video/storyboard/storyboard.spec.json",
              "/vid_e2e/video/design-system/components/footage/clip_s1.mp4",
              "/vid_e2e/video/metadata.md"]:
        assert store.get(p) is not None, f"missing {p}"
    tokens = json.loads(store.get("/vid_e2e/video/design-system/tokens.json").content_text)
    assert tokens["aspect"] == "9:16" and tokens["duration_sec"] == 15
    md = store.get("/vid_e2e/video/metadata.md").content_text
    assert "타이밍 적법성" in md and "passed: True" in md
