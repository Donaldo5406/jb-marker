"""spec 2026-07-03 D1/D2 — 카피 파서(두 형식)·골드 시그널·포스터 상태 매칭."""
import json

from app.providers import demo_fixtures as F


def _directed_prompt(copy_ko: dict, headline_color: str = "#0B1324",
                     headline_px: int = 72) -> str:
    """실 directed 경로와 동일한 프롬프트를 build_director_prompt로 조립(형식 드리프트 방지)."""
    import copy as _c
    from app.gateway.design.directing import build_director_prompt
    spec = _c.deepcopy(F.LAYOUT_SPEC)
    for s in spec["slots"]:
        if s["role"] == "headline":
            s["color"], s["font_px"] = headline_color, headline_px
    spec["copy"] = {"ko": dict(copy_ko)}
    facts = {"금리": "연 3.5%", "만기": "12개월"}
    return build_director_prompt(spec, {}, facts, ["연 3.5%", "12개월 만기"], "ko")


def test_copy_from_prompt_parses_baked_format():
    from app.providers.demo import _copy_from_prompt
    prompt = ("컨셉\n다음 문구를 렌더:\n"
              "- headline: 연 3.5% JB 정기예금 (색 #0B1324, 약 72px 굵게)\n"
              "- body: 12개월 만기, 100만원부터 시작하세요. (색 #1A2332, 약 34px 굵게)\n"
              "- cta: 지금 가입하기\n")
    copy = _copy_from_prompt(prompt)
    # 힌트 괄호는 카피가 아니다 — 스트립되어야 정확 매칭·PIL 베이크 오염 방지.
    assert copy["headline"] == "연 3.5% JB 정기예금"
    assert copy["body"] == "12개월 만기, 100만원부터 시작하세요."
    assert copy["cta"] == "지금 가입하기"


def test_copy_from_prompt_parses_directed_format_roundtrip():
    """AC 2 단위 근거 — 실 build_director_prompt 출력에서 카피가 그대로 복원된다."""
    from app.providers.demo import _copy_from_prompt
    copy = _copy_from_prompt(_directed_prompt(F.COPY["ko"]))
    assert copy["headline"] == F.COPY["ko"]["headline"]
    assert copy["body"] == F.COPY["ko"]["body"]
    assert copy["cta"] == F.COPY["ko"]["cta"]


def test_role_label_mapping_matches_directing():
    """드리프트 가드 — demo의 복제 매핑이 directing._ROLE_KR와 항상 일치(런타임 import 금지 사유: 순환)."""
    from app.gateway.design.directing import _ROLE_KR
    from app.providers.demo import _ROLE_KR_TO_SLOT
    assert _ROLE_KR_TO_SLOT == {label: slot for slot, label in _ROLE_KR.items()}


def test_headline_gold_detects_only_headline_line():
    from app.providers.demo import _headline_gold
    assert _headline_gold(_directed_prompt(F.COPY["ko"], headline_color="#FFD166",
                                           headline_px=88)) is True
    assert _headline_gold(_directed_prompt(F.COPY["ko"])) is False
    # 팔레트 등 다른 줄의 골드는 골드 축이 아니다(오염 가드).
    assert _headline_gold("[디자인 시스템]\n팔레트: #FFD166 #00857C\n"
                          "- headline: 연 3.5% JB 정기예금") is False
    # baked 형식의 헤드라인 힌트 골드도 검출.
    assert _headline_gold("- headline: 연 3.5% JB 정기예금 (색 #FFD166, 약 88px 굵게)") is True


def test_s1_tikitaka_signal_returns_v2_spec():
    """S1 게이트 챗 '캘리/골드' → LAYOUT_SPEC_V2(헤드라인 88px 골드) — 프리뷰 변화의 근원."""
    from app.providers.base import Message
    from app.providers.demo import DemoProvider
    r = json.loads(DemoProvider().complete(
        [Message("user", "헤드라인을 붓펜 캘리그래피 느낌의 골드로 키워줘")],
        model="demo", meta={"studio": "design", "step": "S1"}).text)
    hl = next(s for s in r["layout_spec"]["slots"] if s["role"] == "headline")
    assert hl["color"] == "#FFD166" and hl["font_px"] == 88
    assert "캘리그래피" in r["layout_spec"]["visual_concept"]


def test_s1_default_returns_v1_spec():
    """시그널 없는 S1(최초 실행 '디자인 시작' 포함)은 현행 V1 spec — 오발동 가드."""
    from app.providers.base import Message
    from app.providers.demo import DemoProvider
    r = json.loads(DemoProvider().complete(
        [Message("user", "디자인 시작")],
        model="demo", meta={"studio": "design", "step": "S1"}).text)
    hl = next(s for s in r["layout_spec"]["slots"] if s["role"] == "headline")
    assert hl["color"] == "#0B1324" and hl["font_px"] == 72


def test_layout_spec_v2_shares_v1_invariants():
    """V2는 V1의 계약(슬롯 role·bbox 객체형·logo/disclosure 존재)을 그대로 보존한다."""
    v1_roles = {s["role"] for s in F.LAYOUT_SPEC["slots"]}
    v2_roles = {s["role"] for s in F.LAYOUT_SPEC_V2["slots"]}
    assert v1_roles == v2_roles
    for s in F.LAYOUT_SPEC_V2["slots"]:
        assert isinstance(s["bbox"], dict) and {"x", "y", "w", "h"} <= set(s["bbox"])
    # V1 원본 불변(깊은 복사 확인 — V2 생성이 V1을 오염시키면 안 된다)
    hl1 = next(s for s in F.LAYOUT_SPEC["slots"] if s["role"] == "headline")
    assert hl1["color"] == "#0B1324" and hl1["font_px"] == 72
