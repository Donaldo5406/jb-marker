"""gateway/registry — studio×is_marker → Harness 선택 전수 (spec §10)."""
from app.gateway.registry import select_harness
from app.gateway.harness import PassthroughHarness
from app.gateway.harness_brainstorming import BrainstormingHarness
from app.gateway.harness_design import DesignHarness
from app.gateway.harness_review import ReviewHarness


class _FakeMedia:
    def generate_image(self, prompt, *, aspect="1:1"):
        return b"png"

    def review_image(self, image_bytes, prompt, *, mime="image/png"):
        return None


def _factory():
    return _FakeMedia()


def test_brainstorming_marker():
    assert isinstance(select_harness("brainstorming", True, media_provider_factory=_factory), BrainstormingHarness)


def test_design_marker_injects_media():
    h = select_harness("design", True, media_provider_factory=_factory)
    assert isinstance(h, DesignHarness)


def test_review_marker_lazy_import():
    h = select_harness("review", True, media_provider_factory=_factory)
    assert isinstance(h, ReviewHarness)


def test_non_marker_falls_back_to_passthrough():
    assert isinstance(select_harness("design", False, media_provider_factory=_factory), PassthroughHarness)
    assert isinstance(select_harness("unknown", True, media_provider_factory=_factory), PassthroughHarness)
