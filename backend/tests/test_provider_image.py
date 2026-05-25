"""Provider.generate_image 계약 테스트 (이미지 액터 — marker_api.md M4)."""
from app.providers.base import Provider
from app.providers.fake import FakeProvider


def test_base_generate_image_not_implemented():
    class Bare(Provider):
        def complete(self, messages, *, model, system=None, tools=None, **kw): ...

    import pytest
    with pytest.raises(NotImplementedError):
        Bare().generate_image("배경", aspect="1:1")


def test_fake_generate_image_returns_png_bytes():
    out = FakeProvider().generate_image("연한 블루 그라디언트 배경", aspect="1:1")
    assert isinstance(out, bytes)
    assert out[:8] == b"\x89PNG\r\n\x1a\n"   # PNG 시그니처
