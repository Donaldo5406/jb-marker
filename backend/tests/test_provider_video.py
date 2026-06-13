"""Provider.generate_video 계약 테스트 (영상 액터 — video-harness spec §4)."""
import pytest

from app.providers.base import Provider
from app.providers.fake import FakeProvider
from app.providers.demo import DemoProvider


def test_base_generate_video_not_implemented():
    class Bare(Provider):
        def complete(self, messages, *, model=None, system=None, tools=None, **kw): ...

    with pytest.raises(NotImplementedError):
        Bare().generate_video("배경 footage", aspect="9:16")


def test_fake_generate_video_returns_bytes():
    out = FakeProvider().generate_video("추상 금융 배경", aspect="9:16",
                                        duration_sec=15, fps=30)
    assert isinstance(out, bytes) and len(out) > 0


def test_demo_generate_video_returns_bytes():
    out = DemoProvider().generate_video("추상 금융 배경", aspect="9:16")
    assert isinstance(out, bytes) and len(out) > 0
