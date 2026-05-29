import pytest

from app.gateway.entitlement import EntitlementError
from app.gateway.gateway import MarkerGateway
from app.gateway.harness import HarnessRequest, PassthroughHarness
from app.providers.fake import FakeProvider
from app.vfs.local import LocalVfsStore


@pytest.fixture()
def store(tmp_path):
    s = LocalVfsStore(storage_dir=str(tmp_path))
    s.create_run("r1")
    return s


def _gw(store, override=False):
    return MarkerGateway(store, entitlement_check=lambda uid: False,
                         env_override=override,
                         provider_factory=lambda name: FakeProvider())


def test_gateway_persists_ai_output_to_vfs(store):
    gw = _gw(store)
    req = HarnessRequest(run_id="r1", studio="brainstorming",
                         user_prompt="캠페인 아이디어", provider="fake")
    result = gw.run(req, PassthroughHarness())
    assert "캠페인 아이디어" in result.text
    # 항상 VFS 경유: 산출이 영속됨
    node = store.get(result.output_path)
    assert node is not None and node.content_text == result.text
    assert node.source == "raw"                       # 무료 raw 경로
    assert "grounds" in node.meta


def test_gateway_blocks_marker_without_entitlement(store):
    gw = _gw(store, override=False)
    req = HarnessRequest(run_id="r1", studio="design", user_prompt="x",
                         provider="anthropic", is_marker=True)
    with pytest.raises(EntitlementError):
        gw.run(req, PassthroughHarness())


def test_gateway_allows_marker_with_override(store):
    gw = _gw(store, override=True)
    req = HarnessRequest(run_id="r1", studio="design", user_prompt="x",
                         provider="anthropic", is_marker=True)
    result = gw.run(req, PassthroughHarness())
    assert store.get(result.output_path).source == "marker"


def test_gateway_delegates_to_handle_turn_and_publishes_events():
    from app.gateway.gateway import MarkerGateway
    from app.gateway.harness import PassthroughHarness, HarnessRequest
    from app.providers.fake import FakeProvider
    from app.vfs.local import LocalVfsStore
    s = LocalVfsStore(); s.create_run("rg")
    gw = MarkerGateway(s, entitlement_check=lambda uid: False, env_override=True,
                       provider_factory=lambda name: FakeProvider())
    req = HarnessRequest(run_id="rg", studio="brainstorming", user_prompt="hi", provider="fake")
    res = gw.run(req, PassthroughHarness())
    assert res.output_path == "/rg/brainstorming/passthrough.md"
    assert any(e["type"] == "artifact" for e in res.events)
