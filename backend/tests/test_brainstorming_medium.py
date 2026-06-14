"""medium plumbing — PromptSpec.meta 전달 + HarnessRequest.medium 기본값."""
from app.gateway.prompt import PromptSpec


def test_promptspec_meta_includes_medium():
    p = PromptSpec(persona="x", studio="brainstorming", step="stage_b", medium="video")
    assert p.meta == {"studio": "brainstorming", "step": "stage_b", "medium": "video"}


def test_promptspec_meta_default_medium_image():
    p = PromptSpec(persona="x", studio="brainstorming", step="stage_a")
    assert p.meta.get("medium") == "image"


def test_harness_request_has_medium_default_image():
    from app.gateway.harness import HarnessRequest
    r = HarnessRequest(run_id="r", studio="brainstorming", user_prompt="hi")
    assert r.medium == "image"
    r2 = HarnessRequest(run_id="r", studio="brainstorming", user_prompt="hi", medium="video")
    assert r2.medium == "video"
