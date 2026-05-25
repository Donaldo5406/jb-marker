"""금융 카피 grounding 검증 — 03 nodes/generate.py 이관(Refactor 마이그레이션 전략).

상품 마스터/factsheet에 없는 수치(금리·만기·수수료) 토큰을 카피에서 차단한다.
"""
from __future__ import annotations

import re

_NUM = re.compile(r"\d[\d,.%]*")


class GroundingError(Exception):
    """카피에 마스터 외 수치 토큰이 있을 때."""


def build_corpus(product: dict) -> str:
    """product/factsheet dict의 모든 문자열/리스트 값을 하나의 근거 코퍼스로."""
    parts: list[str] = []
    for v in product.values():
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, (list, tuple)):
            parts.extend(str(x) for x in v)
    return " ".join(parts)


def numeric_tokens(text: str) -> list[str]:
    """텍스트에서 수치 토큰 추출(공백 제거)."""
    return [re.sub(r"\s+", "", t) for t in _NUM.findall(text or "")]


def find_ungrounded(text: str, corpus: str) -> list[str]:
    """corpus에 없는 수치 토큰 목록(비-raise).

    부분문자열이 아닌 토큰-집합 멤버십으로 비교한다("2%"가 "3.2%"에 묻히지 않도록).
    """
    corpus_tokens = set(numeric_tokens(corpus))
    return [t for t in numeric_tokens(text) if t not in corpus_tokens]


def check_asset(asset: dict, product: dict) -> None:
    """headline/body/cta에 마스터 외 수치가 있으면 GroundingError(03 동등)."""
    corpus = build_corpus(product)
    bad: list[str] = []
    for k in ("headline", "body", "cta"):
        bad.extend(find_ungrounded(asset.get(k, ""), corpus))
    if bad:
        raise GroundingError(f"ungrounded numeric tokens: {sorted(set(bad))}")
