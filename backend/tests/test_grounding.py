from app.core.grounding import (GroundingError, build_corpus,
                                numeric_tokens, find_ungrounded, check_asset)


def test_build_corpus_joins_string_and_list_values():
    corpus = build_corpus({"rate": "연 3.5%", "fees": ["없음", "중도해지 0.5%"], "n": 3})
    assert "3.5%" in corpus and "0.5%" in corpus


def test_numeric_tokens_strips_whitespace():
    assert "3.5%" in numeric_tokens("연 3.5% 금리")


def test_find_ungrounded_returns_tokens_absent_from_corpus():
    corpus = build_corpus({"rate": "연 3.5%"})
    assert find_ungrounded("최대 5.0% 금리", corpus) == ["5.0%"]
    assert find_ungrounded("연 3.5% 적금", corpus) == []


def test_find_ungrounded_uses_token_set_not_substring():
    # 부분문자열 false-negative 회귀: "2%"는 "3.2%"의 부분문자열이지만 별개 토큰 → 플래그돼야 함
    assert find_ungrounded("최대 2% 금리", build_corpus({"rate": "연 3.2%"})) == ["2%"]


def test_check_asset_raises_on_ungrounded_headline():
    import pytest
    product = {"rate": "연 3.5%"}
    check_asset({"headline": "연 3.5% 적금", "body": "", "cta": "가입"}, product)  # ok
    with pytest.raises(GroundingError):
        check_asset({"headline": "연 9.9% 특별금리", "body": "", "cta": ""}, product)
