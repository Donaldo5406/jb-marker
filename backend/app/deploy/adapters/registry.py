"""provider id → adapter impl 매핑. 현재 전부 stub."""
from __future__ import annotations

from app.deploy.adapters.base import DeployAdapter
from app.deploy.adapters.stub import StubAdapter

_REGISTRY: dict[str, type[DeployAdapter]] = {
    "email": StubAdapter,
    "kakao": StubAdapter,
    "sms": StubAdapter,
    "naver": StubAdapter,
    "google": StubAdapter,
    "instagram": StubAdapter,
}


def get_adapter(provider_id: str) -> DeployAdapter:
    if provider_id not in _REGISTRY:
        raise KeyError(f"No adapter for provider: {provider_id}")
    return _REGISTRY[provider_id]()
