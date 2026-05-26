"""StubAdapter dispatch 멱등·결과 구조."""
import pytest
from app.deploy.adapters.base import Package, ScheduleSpec
from app.deploy.adapters.stub import StubAdapter
from app.deploy.adapters.registry import get_adapter


def _pkg():
    return Package(channel="email", lang="ko", visual_path="x.png", copy_text="hello", meta={})


def test_dispatch_returns_ok():
    adapter = StubAdapter()
    res = adapter.dispatch("email", _pkg(), ScheduleSpec(send_hour=10), [{"id": "r1"}, {"id": "r2"}])
    assert res.status == "ok"
    assert res.recipients_count == 2
    assert "[STUB]" in res.message


def test_dispatch_idempotent():
    adapter = StubAdapter()
    a = adapter.dispatch("email", _pkg(), ScheduleSpec(send_hour=10), [{"id": "r1"}])
    b = adapter.dispatch("email", _pkg(), ScheduleSpec(send_hour=10), [{"id": "r1"}])
    assert a.message == b.message  # 부수효과 없음


def test_status_property():
    assert StubAdapter().status == "stub"


def test_registry_returns_stub_for_all_six():
    for pid in ["email", "kakao", "sms", "naver", "google", "instagram"]:
        a = get_adapter(pid)
        assert a.status == "stub"


def test_registry_unknown_raises():
    with pytest.raises(KeyError):
        get_adapter("nonexistent")
