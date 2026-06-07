from app.gateway.harness import HarnessRequest, PassthroughHarness
from app.providers.base import Message


def test_passthrough_builds_raw_messages_without_system():
    h = PassthroughHarness()
    req = HarnessRequest(run_id="r1", studio="brainstorming",
                         user_prompt="아이디어 줘", provider="fake")
    system, messages = h.build_messages(req)
    assert system is None                       # 6요소 미적용(raw)
    assert messages[-1] == Message("user", "아이디어 줘")


def test_passthrough_output_path_in_studio():
    h = PassthroughHarness()
    req = HarnessRequest(run_id="r1", studio="design", user_prompt="x", provider="fake")
    assert h.output_path(req) == "/r1/design/_passthrough.md"
