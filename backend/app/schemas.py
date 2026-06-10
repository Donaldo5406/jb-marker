"""HTTP 응답 Pydantic 모델 (spec §8.2) — OpenAPI 명세 표면.

원칙: wire 불변. 가변 키 응답(gate 봉투·usage by_step/by_model·advisor
tool_results·eligibility breakdown)은 dict로 두고 description으로 계약을
문서화한다 — 모델화로 None 키가 추가되거나 미지 키가 탈락하면 행동
변경(P2 wire 계약 위반). `response_model_exclude_none` 사용 금지.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorOut(BaseModel):
    detail: str


class HealthOut(BaseModel):
    status: str


class EntitlementOut(BaseModel):
    marker: bool


class RunCreatedOut(BaseModel):
    run_id: str
    title: str | None


class RunSummaryOut(BaseModel):
    run_id: str
    title: str | None
    # Manifest.created_at 은 str | None (vfs/types.py) — Supabase 행에서 None 가능.
    created_at: str | None
    step_status: dict[str, str]


class RunListOut(BaseModel):
    runs: list[RunSummaryOut]


class VfsNodeOut(BaseModel):
    path: str
    mime: str | None
    source: str | None
    content_text: str | None
    meta: dict[str, Any] | None = Field(
        description="실코드는 항상 dict(빈 dict 포함) — None 허용은 방어적 타입")


class VfsListOut(BaseModel):
    nodes: list[VfsNodeOut]


class UsageTotalsOut(BaseModel):
    input_tokens: int
    output_tokens: int
    images: int
    cost_usd: float
    calls: int


class UsageSummaryOut(BaseModel):
    total: UsageTotalsOut
    by_step: dict[str, dict[str, Any]] = Field(
        description="step별 집계 + by_model(동적 모델명 키) — 동적 키라 dict 유지")
    entries: list[dict[str, Any]]


class GallerySectionOut(BaseModel):
    studio: str
    label: str
    status: str
    has_preview: bool
    groups: list[dict[str, Any]] = Field(
        description="kind별 그룹 {kind, items[]} — items 키: "
                    "path·name·mime·source·is_media·meta (gallery.py _item)")


class GalleryOut(BaseModel):
    run: dict[str, Any] = Field(
        description="run 메타: run_id·title·created_at·current_step·step_status·languages")
    sections: list[GallerySectionOut]
