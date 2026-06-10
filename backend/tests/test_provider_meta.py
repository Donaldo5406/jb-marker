"""Provider.complete meta 인자 수용 + model 완화 (spec §5.2·§5.3)."""
import inspect

from app.providers.base import Message, Provider
from app.providers.fake import FakeProvider


def test_fake_accepts_meta_and_optional_model():
    r = FakeProvider().complete([Message("user", "hi")],
                                meta={"studio": "x", "step": "y"})
    assert r.text  # 수용만 — 무시


def test_demo_accepts_meta_keyword():
    from app.providers.demo import DemoProvider
    r = DemoProvider().complete([Message("user", "hi")], system=None,
                                meta={"studio": "brainstorming", "step": "stage_a"})
    assert r.text is not None


def test_all_providers_declare_meta_and_optional_model():
    """5개 구현체 + ABC가 meta 명시 인자와 model 기본값 None을 선언."""
    from app.providers.anthropic_client import AnthropicProvider
    from app.providers.demo import DemoProvider
    from app.providers.fake import FakeProvider
    from app.providers.google_client import GoogleProvider
    from app.providers.openai_client import OpenAIProvider
    for cls in (Provider, AnthropicProvider, OpenAIProvider, GoogleProvider,
                FakeProvider, DemoProvider):
        sig = inspect.signature(cls.complete)
        assert "meta" in sig.parameters, cls.__name__
        assert sig.parameters["meta"].default is None, cls.__name__
        assert sig.parameters["model"].default is None, cls.__name__
