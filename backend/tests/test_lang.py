"""core/lang.normalize_languages — plan.md languages 다형 입력 → 문자열 코드 리스트."""
from app.core.lang import normalize_languages


def test_string_list_passthrough():
    assert normalize_languages(["ko", "en", "vi", "zh"]) == ["ko", "en", "vi", "zh"]


def test_object_list_extracts_code():
    # 실 Claude 관측 형태: 객체 리스트. code 키 추출.
    raw = [{"code": "ko", "label": "한국어", "primary": True},
           {"code": "en", "label": "English"}]
    assert normalize_languages(raw) == ["ko", "en"]


def test_object_list_is_hashable_after_normalize():
    # 회귀 가드: 정규화 결과가 set/dict 키로 쓸 수 있어야(원래 크래시 원인).
    langs = normalize_languages([{"code": "ko"}, {"code": "en"}])
    assert set(langs) == {"ko", "en"}
    assert {l: 1 for l in langs}  # dict 키 OK


def test_alt_keys_lang_and_language():
    assert normalize_languages([{"lang": "ko"}, {"language": "en"}]) == ["ko", "en"]


def test_label_name_maps_to_code():
    # code 없이 라벨/이름만 있는 경우 흔한 언어명을 코드로 매핑.
    assert normalize_languages([{"label": "한국어"}, {"name": "English"}]) == ["ko", "en"]


def test_comma_separated_string():
    assert normalize_languages("ko, en / vi") == ["ko", "en", "vi"]


def test_single_dict():
    assert normalize_languages({"code": "ko"}) == ["ko"]


def test_uppercase_code_lowercased():
    assert normalize_languages(["KO", "EN"]) == ["ko", "en"]


def test_dedup_preserves_order():
    assert normalize_languages(["ko", "en", "ko"]) == ["ko", "en"]


def test_none_and_empty_default_ko():
    assert normalize_languages(None) == ["ko"]
    assert normalize_languages([]) == ["ko"]
    assert normalize_languages("") == ["ko"]
    assert normalize_languages(123) == ["ko"]


def test_unknown_token_preserved_as_string():
    # 알 수 없는 토큰도 문자열로 보존(해시 가능) — 적어도 크래시는 막는다.
    out = normalize_languages(["ko", {"foo": "bar"}, {"code": "xx"}])
    assert out == ["ko", "xx"]  # code 없는 {foo:bar}는 스킵
    assert all(isinstance(x, str) for x in out)
