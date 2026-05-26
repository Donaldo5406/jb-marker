"""Provider.review_image 추상 + 구현 — vision 입력의 단일 표면."""
import pytest

from app.providers.base import Provider, ProviderResponse
from app.providers.fake import FakeProvider


def test_base_review_image_default_raises():
    """추상 default는 NotImplementedError."""
    class Bare(Provider):
        name = "bare"
        def complete(self, messages, *, model, system=None, tools=None, **kw):
            return ProviderResponse(text="", model=model)
    with pytest.raises(NotImplementedError):
        Bare().review_image(b"\x00", "prompt")


def test_fake_review_image_returns_empty_response():
    """FakeProvider 스텁 — 결정론·테스트용."""
    resp = FakeProvider().review_image(b"\x89PNG", "prompt", mime="image/png")
    assert isinstance(resp, ProviderResponse)
    # 빈 JSON object 또는 findings=[] 형태 — fake는 거짓 finding 만들지 않음
    assert resp.text in ("{}", '{"findings":[]}')


def test_google_provider_review_image_importable():
    """GoogleProvider.review_image가 정의돼 있어야 함(라이브 호출은 키 필요라 import만 검증).

    NOTE: 파일명은 google_client.py이지만 클래스명은 GoogleProvider(코드베이스 컨벤션).
    """
    from app.providers.google_client import GoogleProvider
    assert callable(getattr(GoogleProvider, "review_image", None))
