"""폰트 패밀리 휴리스틱 — 서술형 typography가 CSS font-family로 새는 것을 방지.

실 브레인스토밍의 creative_direction.typography는 종종 폰트명이 아니라 서술 문장
('헤드라인은 굵고 크게(숫자 강조), 본문은 가독성 높은 산세리프')으로 온다. 이를
tokens.font로 폴백하면 design-system 프리뷰 CSS `font-family:`에 그대로 박혀 깨진다.
이 헬퍼로 "폰트명처럼 보이는 값"만 폰트로 채택한다.
"""
from __future__ import annotations

# 폰트명에 등장하지 않는 문장부호·구분자(서술형의 신호).
_BAD_CHARS = set("()[]{}<>。·…\n\t.!?;:/\\\"")

# 서술형 typography 신호어(한국어) — 폰트명이 아니라 "어떻게 쓸지" 설명일 때 등장.
# 짧아서 길이·콤마·공백 검사를 통과하는 서술형('헤드라인 굵게, 본문 산세리프')을 거른다.
_DESC_HINTS = (
    "헤드라인", "본문", "굵게", "굵고", "크게", "작게", "가독",
    "계열", "산세리프", "느낌", "강조", "위주", "톤", "스타일",
)


def looks_like_font_name(value) -> bool:
    """value가 CSS font-family로 안전한 폰트명처럼 보이면 True.

    허용: 'Pretendard', 'Noto Sans KR', 'Pretendard, Inter' 등 짧은 패밀리(명/폴백).
    거부: 서술 문장, 빈/비문자열, 과도하게 길거나 문장부호·서술 신호어를 포함하는 값.
    """
    if not isinstance(value, str):
        return False
    s = value.strip()
    if not s or len(s) > 40:
        return False
    if any(c in _BAD_CHARS for c in s):
        return False
    # 콤마는 폴백 구분(최대 2단계)까지만, 공백 단어 수도 폰트명 수준으로 제한.
    if s.count(",") > 2 or s.count(" ") > 4:
        return False
    if any(h in s for h in _DESC_HINTS):
        return False
    return True
