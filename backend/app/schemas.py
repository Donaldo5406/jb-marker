"""HTTP 응답 Pydantic 모델 (spec §8.2) — OpenAPI 명세 표면.

원칙: wire 불변. 가변 키 응답(gate 봉투·usage by_step/by_model·advisor
tool_results·eligibility breakdown)은 dict로 두고 description으로 계약을
문서화한다 — 모델화로 None 키가 추가되거나 미지 키가 탈락하면 행동
변경(P2 wire 계약 위반). `response_model_exclude_none` 사용 금지.

고정 키셋이라도 깊은 중첩(gallery groups/run 등)은 dict+description을 허용
— 1단계 키셋만 모델화가 기준.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ── 공용 ──

class ErrorOut(BaseModel):
    detail: str


# 라우트 responses= 합성용 공용 상수 — 인증 라우트는 AUTH, run-scoped는 OWNER를 spread.
AUTH_RESPONSES: dict = {401: {"model": ErrorOut}}
OWNER_RESPONSES: dict = {**AUTH_RESPONSES, 404: {"model": ErrorOut}}


# ── meta ──

class HealthOut(BaseModel):
    status: str


class EntitlementOut(BaseModel):
    marker: bool


# ── runs ──

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


# ── vfs ──

class VfsNodeOut(BaseModel):
    path: str
    mime: str | None
    source: str | None
    content_text: str | None
    meta: dict[str, Any] | None = Field(
        description="실코드는 항상 dict(빈 dict 포함) — None 허용은 방어적 타입")


class VfsListOut(BaseModel):
    nodes: list[VfsNodeOut]


# ── observability ──

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


# ── history ──

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


# ── session ──
# heartbeat는 단일 모델 불가 — "세션 없음"은 정확 4키(status: None 포함),
# "있음"은 정확 8키(liveness 파생 뷰). exists Literal(True/False)이
# 배타 판별 — smart union, 순서 비의존 (session.py 라우터 주석 참조).

class SessionMissingOut(BaseModel):
    kind: Literal["heartbeat"]
    exists: Literal[False]
    status: None = None
    resumable: bool


class SessionLivenessOut(BaseModel):
    kind: Literal["heartbeat"]
    exists: Literal[True]
    liveness: str
    status: str
    # warn_at/suspend_at = rec.updated_at_ms + 임계(ms) — int 확정 (liveness.py heartbeat_view)
    warn_at: int
    suspend_at: int
    expires_at: int | None
    resumable: bool


class SessionRestoredOut(BaseModel):
    kind: Literal["restored"]
    run_id: str
    studio: str
    status: str


class SessionExpiredOut(BaseModel):
    kind: Literal["expired"]
    reason: str


class SessionSuspendOut(BaseModel):
    kind: Literal["suspended"]
    status: str


class SessionListItemOut(BaseModel):
    studio: str
    status: str
    updated_at_ms: int
    expires_at: int | None


class SessionListOut(BaseModel):
    kind: Literal["session_list"]
    sessions: list[SessionListItemOut]


# ── deploy ──

class MatrixCellOut(BaseModel):
    channel: str
    lang: str


class DeploySetupOut(BaseModel):
    matrix: list[MatrixCellOut]
    step_status: str


class EligibilityOut(BaseModel):
    total: int
    eligible_count: int
    excluded_count: int
    breakdown: list[dict[str, Any]] = Field(
        description="정책별(§50/§15·§16) 사유 분해 — 항목 형태 "
                    "{policy,label,citation,count,reasons:[{status,label,count}]} "
                    "(eligibility.py _build_breakdown, _POLICY_ORDER 순)")


class PackageOut(BaseModel):
    package_id: str
    status: str
    reason: str | None


class AdvisorOkOut(BaseModel):
    status: Literal["ok"]
    text: str
    tool_results: list[dict[str, Any]] = Field(
        description="도구 실행 결과 — 항목 형태 가변({name,status[,reason]}|{name,output}|{name,status,failures})")


class AdvisorErrorOut(BaseModel):
    status: Literal["error"]
    message: str


class DispatchOut(BaseModel):
    step_status: Literal["PASS"]
    simulation: list[dict[str, Any]] = Field(
        description="채널×언어 셀 결과 — {channel,lang,status,message,recipients_count} 또는 skipped 셀 {channel,lang,status,reason}")


class DeployStateOut(BaseModel):
    step_status: str
    selected_providers: list[str]
    matrix: list[MatrixCellOut]


# ── gateway ──

class GatewayRunOut(BaseModel):
    output_path: str | None
    text: str
    gate: dict[str, Any] | None = Field(
        description="GateEnvelope(P2 wire 계약): kind=ask|confirm|status + actions, "
                    "None 필드 생략(가변 키) — 모델화 금지, dict 유지")
    meta: dict[str, Any]
