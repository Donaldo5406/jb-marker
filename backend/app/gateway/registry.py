"""studio×is_marker → Harness 선택 (server.py if/elif에서 추출, spec §8.1).

DesignHarness는 모듈 글로벌 — test_mock_mode가 monkeypatch.setattr(registry,
"DesignHarness", Spy)로 패치하는 표면이므로 함수 내부에서 호출 시점 글로벌
조회를 유지한다(로컬 바인딩 금지). BrainstormingHarness는 대칭 유지용 글로벌.
ReviewHarness만 호출 시점 지연 import — 테스트가 harness_review 모듈을 패치.
"""
from __future__ import annotations

from .harness import Harness, PassthroughHarness
from .harness_brainstorming import BrainstormingHarness
from .harness_design import DesignHarness


def select_harness(studio: str, is_marker: bool, *, media_provider_factory) -> Harness:
    if studio == "brainstorming" and is_marker:
        return BrainstormingHarness()
    if studio == "design" and is_marker:
        return DesignHarness(image_provider=media_provider_factory())
    if studio == "review" and is_marker:
        from .harness_review import ReviewHarness
        return ReviewHarness(vision_provider=media_provider_factory())
    if studio == "video" and is_marker:
        from .harness_video import VideoHarness
        return VideoHarness(video_provider=media_provider_factory())
    return PassthroughHarness()
