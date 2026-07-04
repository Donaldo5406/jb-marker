"""엔타이틀먼트 단일 choke point (Refactor C4).

Marker 하네스·Deploy 어드바이저 = 유료 티어($100/월) 전용.
무료 = raw Claude/GPT/Gemini. 실 PG 청구는 Non-goal → override 플래그로 데모 토글.
"""
from __future__ import annotations


class EntitlementError(PermissionError):
    pass


def check_entitlement(*, is_marker: bool, override: bool) -> None:
    if is_marker and not override:
        # 메시지에 우회 경로를 명시 — 라이브 시연에서 조용한 402로 막히면 원인을
        # 못 찾는다. Mock 모드(무료·결정적) 또는 운영 엔타이틀먼트 오버라이드로 우회.
        raise EntitlementError(
            "Marker/Advisor 기능은 유료 티어($100/월) 전용입니다. "
            "시연은 Mock 모드로 실행하거나 운영 환경에 엔타이틀먼트 오버라이드를 설정하세요.")
