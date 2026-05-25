import pytest

from app.providers.base import Message
from app.providers.fake import FakeProvider
from app.providers.registry import get_provider


def test_fake_provider_echoes():
    p = FakeProvider()
    resp = p.complete([Message("user", "안녕")], model="fake-1")
    assert "안녕" in resp.text
    assert resp.model == "fake-1"


def test_registry_returns_fake():
    assert isinstance(get_provider("fake"), FakeProvider)


def test_registry_unknown_raises():
    with pytest.raises(ValueError):
        get_provider("nope")
