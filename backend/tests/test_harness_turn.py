"""M3 Task 3: handle_turn 턴 핸들러 격상 + HarnessResult 확장 + Passthrough 이식."""


def _local_store():
    from app.vfs.local import LocalVfsStore
    s = LocalVfsStore()
    s.create_run("r1", title="t")
    return s


def test_passthrough_handle_turn_persists_and_returns():
    from app.gateway.harness import PassthroughHarness, HarnessRequest
    from app.providers.fake import FakeProvider
    s = _local_store()
    req = HarnessRequest(run_id="r1", studio="brainstorming", user_prompt="안녕", provider="fake")
    res = PassthroughHarness().handle_turn(req, provider=FakeProvider(), store=s)
    assert res.text.startswith("echo:") or "echo" in res.text
    assert res.output_path == "/r1/brainstorming/passthrough.md"
    assert s.get("/r1/brainstorming/passthrough.md") is not None
    assert res.ask is None
    assert any(e["type"] == "artifact" for e in res.events)


def test_harness_request_has_answer_and_bypass_defaults():
    from app.gateway.harness import HarnessRequest
    req = HarnessRequest(run_id="r", studio="brainstorming", user_prompt="p", provider="fake")
    assert req.answer is None and req.bypass is False
