"""엔타이틀먼트 단일 choke point (Refactor C4).

Marker 하네스·Deploy 어드바이저 = 유료 티어($100/월) 전용.
무료 = raw Claude/GPT/Gemini. 실 PG 청구는 Non-goal → override 플래그로 데모 토글.
"""
from __future__ import annotations


class EntitlementError(PermissionError):
    pass


def check_entitlement(*, is_marker: bool, override: bool) -> None:
    if is_marker and not override:
        raise EntitlementError("Marker/Advisor 기능은 유료 티어($100/월) 전용입니다.")
