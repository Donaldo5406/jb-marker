import pytest

from app.gateway.entitlement import EntitlementError, check_entitlement
from app.gateway.gateway import MarkerGateway
from app.gateway.harness import HarnessRequest, PassthroughHarness
from app.providers.fake import FakeProvider
from app.vfs.local import LocalVfsStore


def test_free_tier_allows_raw():
    check_entitlement(is_marker=False, override=False)   # no raise


def test_free_tier_blocks_marker():
    with pytest.raises(EntitlementError):
        check_entitlement(is_marker=True, override=False)


def test_override_allows_marker():
    check_entitlement(is_marker=True, override=True)      # no raise


def _store(tmp_path):
    s = LocalVfsStore(storage_dir=str(tmp_path))
    s.create_run("r1")
    return s


def test_gateway_blocks_marker_when_user_not_entitled(tmp_path):
    """env_override=False + check(uid)=False → marker는 PermissionError."""
    store = _store(tmp_path)
    gw = MarkerGateway(store,
                       entitlement_check=lambda uid: False,
                       provider_factory=lambda name: FakeProvider())
    req = HarnessRequest(run_id="r1", studio="design", user_prompt="x",
                         provider="fake", is_marker=True, user_id="alice")
    with pytest.raises(EntitlementError):
        gw.run(req, PassthroughHarness())


def test_gateway_allows_marker_when_user_entitled(tmp_path):
    """env_override=False라도 해당 user_id가 entitled면 통과."""
    store = _store(tmp_path)
    entitled = {"alice"}
    gw = MarkerGateway(store,
                       entitlement_check=lambda uid: uid in entitled,
                       provider_factory=lambda name: FakeProvider())
    req = HarnessRequest(run_id="r1", studio="design", user_prompt="x",
                         provider="fake", is_marker=True, user_id="alice")
    result = gw.run(req, PassthroughHarness())
    assert store.get(result.output_path).source == "marker"


def test_gateway_per_user_isolation(tmp_path):
    """alice entitled, bob 아님 → 같은 게이트웨이가 user_id별로 다르게 게이트."""
    store = _store(tmp_path)
    entitled = {"alice"}
    gw = MarkerGateway(store,
                       entitlement_check=lambda uid: uid in entitled,
                       provider_factory=lambda name: FakeProvider())
    ok = HarnessRequest(run_id="r1", studio="design", user_prompt="x",
                        provider="fake", is_marker=True, user_id="alice")
    gw.run(ok, PassthroughHarness())  # no raise
    blocked = HarnessRequest(run_id="r1", studio="design", user_prompt="x",
                             provider="fake", is_marker=True, user_id="bob")
    with pytest.raises(EntitlementError):
        gw.run(blocked, PassthroughHarness())
