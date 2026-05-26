"""providers.yaml 로더 + Pydantic 검증."""
from __future__ import annotations

import pathlib
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class ImageSize(BaseModel):
    w: int
    h: int
    name: str


class CopyLimits(BaseModel):
    title: int = Field(ge=0)
    body: int = Field(ge=0)


class ProviderSpec(BaseModel):
    image_sizes: list[ImageSize] = Field(default_factory=list)
    copy_limits: CopyLimits
    required_disclosures: list[str] = Field(default_factory=list)


class Provider(BaseModel):
    id: str
    name: str
    logo_path: str
    channel_type: Literal["email", "messenger", "sms", "ad", "social"]
    adapter_status: Literal["stub", "live"]
    priority: int = Field(ge=1)
    credentials_schema: dict[str, str]
    spec: ProviderSpec


def load_providers() -> list[Provider]:
    path = pathlib.Path(__file__).parent / "providers.yaml"
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return [Provider.model_validate(p) for p in raw]


def get_provider(provider_id: str) -> Provider:
    for p in load_providers():
        if p.id == provider_id:
            return p
    raise KeyError(f"Unknown provider: {provider_id}")
