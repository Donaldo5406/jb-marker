"""plan.md frontmatter의 languages 필드를 문자열 언어코드 리스트로 정규화.

실 LLM(브레인스토밍 plan.md 작성)은 languages를 다양한 형태로 출력한다:
  - ["ko", "en"]                                              (문자열 리스트 — Mock/이상적)
  - [{"code": "ko", "label": "한국어", "primary": true}, ...]  (객체 리스트 — 실 Claude 관측)
  - "ko, en"                                                  (콤마 구분 문자열)
  - {"code": "ko"}                                            (단일 객체)

downstream(NOTICES.get(lang)·copy.get(lang)·파일경로 `.../{lang}/main.scene`)은
'해시 가능한 문자열 코드'를 전제하므로, 객체가 그대로 흘러가면 TypeError(unhashable dict)로
Design S2c/S3·Review가 크래시한다(Mock은 문자열이라 안 터지던 잠재버그). 이 함수가 단일 정규화 지점이다.
"""
from __future__ import annotations

import re

_DEFAULT = ["ko"]

# 객체 형태일 때 코드 추출 우선순위 키.
_CODE_KEYS = ("code", "lang", "language", "value", "id", "iso", "label", "name")

# 라벨/이름이 코드 대신 들어온 경우의 매핑(흔한 4개 언어).
_NAME_TO_CODE = {
    "korean": "ko", "한국어": "ko", "국문": "ko",
    "english": "en", "영어": "en",
    "vietnamese": "vi", "베트남어": "vi", "tiếng việt": "vi",
    "chinese": "zh", "중국어": "zh", "중문": "zh",
}

# BCP-47 비슷한 코드 패턴(2~3 알파 + 선택 지역 서브태그).
_CODE_RE = re.compile(r"^[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,4})?$")


def _coerce(token: str) -> str | None:
    t = (token or "").strip()
    if not t:
        return None
    low = t.lower()
    if low in _NAME_TO_CODE:
        return _NAME_TO_CODE[low]
    if _CODE_RE.match(t):
        return low            # "KO" → "ko", "en-US" → "en-us"
    return t                  # 알 수 없는 토큰도 보존(폴백) — 적어도 해시 가능 문자열


def _from_item(item) -> str | None:
    if isinstance(item, str):
        return _coerce(item)
    if isinstance(item, dict):
        for k in _CODE_KEYS:
            v = item.get(k)
            if isinstance(v, str) and v.strip():
                return _coerce(v)
    return None


def normalize_languages(raw) -> list[str]:
    """languages를 문자열 코드 리스트로 정규화.

    알 수 없으면 ['ko']. 순서 보존·중복 제거. 모든 항목이 해시 가능한 문자열임을 보장한다.
    """
    if raw is None:
        return list(_DEFAULT)
    if isinstance(raw, str):
        items: list = [p for p in re.split(r"[,\s/|]+", raw) if p]
    elif isinstance(raw, dict):
        items = [raw]
    elif isinstance(raw, (list, tuple)):
        items = list(raw)
    else:
        return list(_DEFAULT)

    out: list[str] = []
    seen: set[str] = set()
    for it in items:
        code = _from_item(it)
        if code and code not in seen:
            seen.add(code)
            out.append(code)
    return out or list(_DEFAULT)
