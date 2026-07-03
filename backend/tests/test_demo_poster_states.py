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


def test_poster_state_2x2_matrix():
    from app.providers.demo import _poster_state
    viol = dict(F.COPY_VIOLATING["ko"])
    clean = dict(F.COPY["ko"])
    gold_prompt = '- headline: x (색 #FFD166, 약 88px 굵게)'
    assert _poster_state(viol, "") == "violating"
    assert _poster_state(viol, gold_prompt) == "violating_gold"
    assert _poster_state(clean, "") == "final"
    assert _poster_state(clean, gold_prompt) == "v2"
    # 미지 카피(en 등 비ko·임의 편집) → None → PIL 폴백(AC 5)
    assert _poster_state(dict(F.COPY["en"]), "") is None
    assert _poster_state({}, "") is None


def _seed_fixture_dir(tmp_path, monkeypatch, states=("violating",)):
    """tmp fixture 디렉토리에 상태별 유효 PNG를 심고 _POSTER_DIR을 돌려놓는다."""
    for st in states:
        (tmp_path / f"poster_{st}.png").write_bytes(F.placeholder_png(64, 80))
    monkeypatch.setattr(F, "_POSTER_DIR", str(tmp_path))


def test_load_poster_fixture_reads_file_or_none(tmp_path, monkeypatch):
    _seed_fixture_dir(tmp_path, monkeypatch, states=("violating",))
    png = F.load_poster_fixture("violating")
    assert png and png[:8] == b"\x89PNG\r\n\x1a\n"
    assert F.load_poster_fixture("final") is None        # 파일 부재 → None
    assert F.load_poster_fixture("없는상태") is None      # 미지 상태 → None


def test_generate_image_returns_fixture_on_state_match(tmp_path, monkeypatch):
    """위반 카피 베이크 프롬프트(baked 형식) → poster_violating fixture 바이트 그대로(AC 4)."""
    from app.providers.demo import DemoProvider
    _seed_fixture_dir(tmp_path, monkeypatch, states=("violating",))
    expected = F.load_poster_fixture("violating")
    prompt = ("컨셉\n- headline: 업계 최고 금리 JB 정기예금\n"
              "- body: 연 4.0% 12개월 만기, 100만원부터 시작하세요.\n- cta: 지금 가입하기")
    assert DemoProvider().generate_image(prompt, aspect="4:5") == expected


def test_generate_image_directed_prompt_matches_fixture(tmp_path, monkeypatch):
    """directed 프롬프트에서도 상태 매칭(AC 2+4 결합) — 실 build_director_prompt 산출로 검증."""
    from app.providers.demo import DemoProvider
    _seed_fixture_dir(tmp_path, monkeypatch, states=("v2",))
    expected = F.load_poster_fixture("v2")
    prompt = _directed_prompt(F.COPY["ko"], headline_color="#FFD166", headline_px=88)
    assert DemoProvider().generate_image(prompt, aspect="4:5") == expected


def test_generate_image_falls_back_to_pil_when_no_fixture(tmp_path, monkeypatch):
    """fixture 파일 부재 시 현행 PIL 베이크 폴백 — 완주 보장(AC 5). 배경 원본과 달라야 한다."""
    from app.providers.demo import DemoProvider
    monkeypatch.setattr(F, "_POSTER_DIR", str(tmp_path))   # 빈 디렉토리 = fixture 전무
    prompt = "컨셉\n- headline: 연 3.5% JB 정기예금\n- body: 12개월 만기\n- cta: 가입"
    png = DemoProvider().generate_image(prompt, aspect="4:5")
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert png != F.load_poster_bg()   # 카피가 합성됨(맨 배경 아님)
