"""advisor 도구 화이트리스트 — read_review·read_eligibility·write_d2_copy."""
from __future__ import annotations

from typing import Literal


class ToolNotAllowed(Exception):
    """미허용 도구 호출 — transcript에 tool_blocked 이벤트로 기록."""


ALLOWED: set[str] = {"read_review", "read_eligibility", "write_d2_copy"}


TOOL_SCHEMAS = [
    {
        "name": "read_review",
        "description": "Review 통과 텍스트 + grounding 토큰셋 읽기(read-only)",
        "input_schema": {
            "type": "object",
            "properties": {"package_id": {"type": "string"}},
            "required": ["package_id"],
        },
    },
    {
        "name": "read_eligibility",
        "description": "D1 결과(발송대상·제외·캘린더) 읽기(read-only). 조언 컨텍스트용.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "write_d2_copy",
        "description": "채널 규격에 맞춘 적응 카피 제출. grounding 검증 후 영속.",
        "input_schema": {
            "type": "object",
            "properties": {
                "package_id": {"type": "string"},
                "adapted_text": {"type": "string"},
            },
            "required": ["package_id", "adapted_text"],
        },
    },
]


def assert_allowed(tool_name: str) -> None:
    if tool_name not in ALLOWED:
        raise ToolNotAllowed(f"Tool '{tool_name}' is not in advisor whitelist {sorted(ALLOWED)}")
