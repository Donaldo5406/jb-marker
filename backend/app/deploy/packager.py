"""D2 패키저 — copy_limits 분기 + disclosures append. advisor 호출은 라우트가 트리거."""
from __future__ import annotations

from typing import Literal

from app.deploy.providers import Provider


def needs_advisor(copy_text: str, provider: Provider) -> tuple[bool, str]:
    """copy_limits 위반 여부 + 사유."""
    limits = provider.spec.copy_limits
    if limits.body and len(copy_text) > limits.body:
        return True, f"body length {len(copy_text)} > limit {limits.body}"
    return False, "within limits"


def append_disclosures(copy_text: str, provider: Provider) -> str:
    """필수고지 append (코드 책임 — advisor 손대지 않음)."""
    parts = [copy_text]
    for d in provider.spec.required_disclosures:
        if d not in copy_text:
            parts.append(d)
    return "\n\n".join(parts)


def package_channel(
    *,
    channel: str,
    lang: str,
    original_copy: str,
    provider: Provider,
    visual_path: str,
) -> dict:
    """패키지 dict 생성. advisor 필요 시 status='needs_advisor', 아니면 'ok'."""
    needs, reason = needs_advisor(original_copy, provider)
    if needs:
        return {
            "status": "needs_advisor",
            "channel": channel,
            "lang": lang,
            "reason": reason,
            "original_text": original_copy,
            "disclosures": provider.spec.required_disclosures,
            "visual_path": visual_path,
        }

    final_copy = append_disclosures(original_copy, provider)
    return {
        "status": "ok",
        "channel": channel,
        "lang": lang,
        "copy_text": final_copy,
        "original_text": original_copy,
        "disclosures": provider.spec.required_disclosures,
        "visual_path": visual_path,
        "grounding_check": "n/a",  # advisor 미경유
    }
