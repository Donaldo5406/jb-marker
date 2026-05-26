"""advisor 출력 검증 — 4 invariants."""
from __future__ import annotations

import re
from dataclasses import dataclass


_NUMBER_RE = re.compile(r"\d[\d,\.]*%?")
_TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]+")

# 안전 동의어 — 적응 카피가 원본에 없어도 허용되는 토큰
_ALLOWED_PARAPHRASE: set[str] = {
    "지금", "오늘", "확인", "안내", "공지", "광고", "수신거부", "더보기", "자세히",
}


@dataclass
class GroundingResult:
    ok: bool
    failures: list[str]
    original_tokens: set[str]
    adapted_tokens: set[str]


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text))


def _numbers(text: str) -> list[str]:
    return _NUMBER_RE.findall(text)


def check(original: str, adapted: str, disclosures: list[str]) -> GroundingResult:
    """4 invariants — 모두 통과해야 ok=True."""
    failures: list[str] = []

    orig_tokens = _tokens(original)
    adp_tokens = _tokens(adapted)

    # 1: 토큰셋 부분집합 + 안전 동의어
    new_tokens = adp_tokens - orig_tokens - _ALLOWED_PARAPHRASE
    if new_tokens:
        failures.append(f"unknown_tokens: {sorted(new_tokens)[:5]}")

    # 2: 숫자 매칭
    orig_nums = sorted(_numbers(original))
    adp_nums = sorted(_numbers(adapted))
    if orig_nums != adp_nums:
        failures.append(f"number_mismatch: orig={orig_nums} adapted={adp_nums}")

    # 3: 필수고지 매칭
    missing = [d for d in disclosures if d not in adapted]
    if missing:
        failures.append(f"missing_disclosures: {missing}")

    # 4: 신조어 — (1)과 동일 검증으로 흡수 (안전 동의어 외 신토큰 ✗)

    return GroundingResult(
        ok=not failures,
        failures=failures,
        original_tokens=orig_tokens,
        adapted_tokens=adp_tokens,
    )
