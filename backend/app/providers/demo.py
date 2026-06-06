"""DemoProvider — 시연용 Mock 파이프라인. system 마커로 단계를 감지해 결정적 fixture 반환.

FakeProvider(echo)와 달리 각 하네스가 기대하는 JSON을 돌려줘 BrainStorming→Deploy 전 구간을
끝까지 완주시킨다. 단계 감지는 system 프롬프트의 안정적 마커에 의존(프롬프트 변경 시 통합 테스트가 경보).
"""
from __future__ import annotations

import json

from . import demo_fixtures as F
from .base import Provider, ProviderResponse


def _spec_json() -> str:
    return json.dumps({"reply": "스펙 초안을 정리했어요.", "document": F.SPEC_MD,
                       "ask": None, "ready": True}, ensure_ascii=False)


def _plan_json() -> str:
    return json.dumps({"reply": "구현 계획을 정리했어요.", "document": F.PLAN_MD,
                       "ask": None, "ready": True}, ensure_ascii=False)


def _layout_json() -> str:
    return json.dumps({"reply": "러프 완성", "layout_spec": F.LAYOUT_SPEC, "ready": True},
                      ensure_ascii=False)


def _copy_json() -> str:
    return json.dumps({"copy": F.COPY}, ensure_ascii=False)


def _critic_json() -> str:
    return json.dumps({"scores": F.CRITIC_SCORES}, ensure_ascii=False)


def _empty_findings() -> str:
    return json.dumps({"findings": []}, ensure_ascii=False)


def _reconcile_json() -> str:
    return json.dumps({"recommendations": [], "conflicts_resolved": []}, ensure_ascii=False)


def _detect(system: str) -> str:
    """system 마커로 단계 판별 → 해당 fixture JSON. 미매칭은 안전 기본(빈 reply, ready=false)."""
    s = system or ""
    if "[Stage A]" in s:
        return _spec_json()
    if "[Stage B]" in s:
        return _plan_json()
    if "[S1 Rough]" in s:
        return _layout_json()
    if "[S2b" in s:
        return _copy_json()
    if "[자기-크리틱]" in s:
        return _critic_json()
    if "reconciler" in s:                       # Review R3 (PERSONA_C)
        return _reconcile_json()
    if "검토관" in s or "법령" in s or "법률" in s:  # Review R1/R2 (PERSONA_A/B)
        return _empty_findings()
    return json.dumps({"reply": "", "ready": False}, ensure_ascii=False)


class DemoProvider(Provider):
    name = "demo"

    def complete(self, messages, *, model, system=None, tools=None, **kwargs) -> ProviderResponse:
        return ProviderResponse(text=_detect(system or ""), model="demo", raw=None)

    def generate_image(self, prompt: str, *, aspect: str = "1:1") -> bytes:
        return F.placeholder_png()

    def review_image(self, image_bytes, prompt, *, mime="image/png") -> ProviderResponse:
        return ProviderResponse(text=_empty_findings(), model="demo")
