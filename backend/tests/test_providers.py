"""providers.yaml 로더 + Pydantic 검증."""
import pytest
from pydantic import ValidationError

from app.deploy.providers import Provider, get_provider, load_providers
from app.providers.base import Message
from app.providers.fake import FakeProvider
from app.providers.registry import get_provider as get_llm_provider


def test_fake_provider_echoes():
    p = FakeProvider()
    resp = p.complete([Message("user", "안녕")], model="fake-1")
    assert "안녕" in resp.text
    assert resp.model == "fake-1"


def test_registry_returns_fake():
    assert isinstance(get_llm_provider("fake"), FakeProvider)


def test_registry_unknown_raises():
    with pytest.raises(ValueError):
        get_llm_provider("nope")


# ---------------------------------------------------------------------------
# M6 Task 5 — deploy providers catalog (providers.yaml + Pydantic loader)
# ---------------------------------------------------------------------------


def test_loads_six_providers():
    providers = load_providers()
    ids = {p.id for p in providers}
    assert ids == {"email", "kakao", "sms", "naver", "google", "instagram"}


def test_email_priority_1():
    p = get_provider("email")
    assert p.priority == 1
    assert p.adapter_status == "stub"


def test_kakao_priority_2():
    p = get_provider("kakao")
    assert p.priority == 2


def test_all_have_required_fields():
    for p in load_providers():
        assert p.spec.copy_limits.body > 0 or p.id == "sms"  # SMS는 body 90자
        assert p.logo_path.endswith(".svg")


def test_invalid_priority_zero_rejected():
    with pytest.raises(ValidationError):
        Provider.model_validate({
            "id": "x", "name": "x", "logo_path": "/x.svg",
            "channel_type": "email", "adapter_status": "stub", "priority": 0,
            "credentials_schema": {}, "spec": {"copy_limits": {"title": 1, "body": 1}},
        })


def test_unknown_provider_raises():
    with pytest.raises(KeyError):
        get_provider("nonexistent")
