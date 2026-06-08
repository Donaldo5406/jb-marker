"""폰트 패밀리 휴리스틱 — 서술형 typography가 CSS font-family로 새는 것 방지."""
from app.core.fonts import looks_like_font_name


def test_accepts_real_font_names():
    assert looks_like_font_name("Pretendard")
    assert looks_like_font_name("Inter")
    assert looks_like_font_name("Noto Sans KR")
    assert looks_like_font_name("Pretendard, Inter")          # 폴백 1단계
    assert looks_like_font_name("Pretendard, Inter, Arial")   # 폴백 2단계


def test_rejects_descriptive_typography():
    # 실 브레인스토밍이 쓰는 서술형 문장 — 폰트명 아님
    assert not looks_like_font_name(
        "헤드라인은 굵고 크게(숫자 강조), 본문은 가독성 높은 산세리프")
    assert not looks_like_font_name("굵고 신뢰감 있는 산세리프 계열로 통일")


def test_rejects_empty_and_non_string():
    assert not looks_like_font_name("")
    assert not looks_like_font_name("   ")
    assert not looks_like_font_name(None)
    assert not looks_like_font_name(123)
    assert not looks_like_font_name(["Inter"])


def test_rejects_overlong_and_punctuated():
    assert not looks_like_font_name("A" * 41)               # 과도하게 긺
    assert not looks_like_font_name("Inter. 본문용")          # 마침표
    assert not looks_like_font_name("Bold (headline)")       # 괄호
    assert not looks_like_font_name("a, b, c, d")            # 콤마 3개(폴백 한도 초과)
