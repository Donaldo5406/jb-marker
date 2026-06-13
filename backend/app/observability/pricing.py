"""모델별 토큰·이미지 단가 (USD).

공식 가격대 추정치. 정확한 빌링은 provider 콘솔 참고.
요율 변경 시 이 표만 갱신.
"""
from __future__ import annotations

# USD per 1M tokens. (input, output)
_TEXT_PRICES_PER_MILLION: dict[str, tuple[float, float]] = {
    # Anthropic Claude
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-haiku-4-5": (0.80, 4.0),
    # OpenAI
    "gpt-4o": (2.50, 10.0),
    "gpt-4o-mini": (0.15, 0.60),
    # Google Gemini
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-2.5-flash": (0.10, 0.40),
    "gemini-2.5-flash-image": (0.10, 0.40),  # 텍스트 부분 (이미지는 아래)
    "gemini-3-pro-image": (2.0, 12.0),       # pro 티어 텍스트 부분 — 추정, provider 콘솔로 확정
    "gemini-3.1-flash-image": (0.10, 0.40),  # 추정
    # Fake / unknown
    "fake": (0.0, 0.0),
    "fake-1": (0.0, 0.0),
}

# 이미지 생성 USD per image.
_IMAGE_PRICES: dict[str, float] = {
    "gemini-2.5-flash-image": 0.04,
    "gemini-3-pro-image": 0.24,       # pro 티어 — 추정, 콘솔 확정 필요
    "gemini-3.1-flash-image": 0.06,   # 추정
    "fake": 0.0,
}


def text_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """텍스트 호출 비용 추정. 모델 미상이면 0 (표 갱신 신호)."""
    rates = _TEXT_PRICES_PER_MILLION.get(model)
    if not rates:
        return 0.0
    in_rate, out_rate = rates
    return (input_tokens / 1_000_000.0) * in_rate + (output_tokens / 1_000_000.0) * out_rate


def image_cost_usd(model: str, count: int) -> float:
    """이미지 생성 비용 추정 (모델 미상이면 0)."""
    rate = _IMAGE_PRICES.get(model)
    if rate is None:
        return 0.0
    return float(count) * rate


def is_known(model: str) -> bool:
    return model in _TEXT_PRICES_PER_MILLION or model in _IMAGE_PRICES
