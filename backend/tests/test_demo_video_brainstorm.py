"""demo 브레인스토밍 medium=video — spec.md/plan.md가 medium:video를 산출하는지."""
import json
from app.providers.base import Message
from app.providers.demo import DemoProvider


def _meta(step, medium):
    return {"studio": "brainstorming", "step": step, "medium": medium}


def test_stage_a_video_spec_has_medium_video():
    demo = DemoProvider()
    msgs = [Message("user", "정기예금 영상"), Message("assistant", "?"),
            Message("user", "2030"), Message("assistant", "?"), Message("user", "국문만")]
    resp = demo.complete(msgs, system="", meta=_meta("stage_a", "video"))
    data = json.loads(resp.text)
    assert "medium: video" in (data.get("document") or "")


def test_stage_b_video_plan_has_medium_video():
    demo = DemoProvider()
    system = "[현재 plan.md]\nmedium: video\n초안"
    resp = demo.complete([Message("user", "go")], system=system, meta=_meta("stage_b", "video"))
    data = json.loads(resp.text)
    assert "medium: video" in (data.get("document") or "")
    assert data.get("ready") is True


def test_stage_b_image_unchanged():
    demo = DemoProvider()
    system = "[현재 plan.md]\n초안"
    resp = demo.complete([Message("user", "go")], system=system, meta=_meta("stage_b", "image"))
    data = json.loads(resp.text)
    assert "creative_direction" in (data.get("document") or "")


def test_video_spec_passes_sufficiency_gate():
    """demo VIDEO_SPEC_MD가 REQUIRED_SPEC_FIELDS를 모두 충족해 보충 게이트에 막히지 않는다."""
    from app.gateway.harness_brainstorming import REQUIRED_SPEC_FIELDS, _frontmatter_keys
    from app.providers import demo_fixtures as F
    keys = _frontmatter_keys(F.VIDEO_SPEC_MD)
    missing = REQUIRED_SPEC_FIELDS - keys
    assert missing == set(), f"VIDEO_SPEC_MD missing required spec fields: {sorted(missing)}"
