"""spec 2026-07-03 D1/D2 — 카피 파서(두 형식)·골드 시그널·포스터 상태 매칭."""
import json

from app.providers import demo_fixtures as F


def _directed_prompt(copy_map: dict, headline_color: str = "#0B1324",
                     headline_px: int = 72, lang: str = "ko") -> str:
    """실 directed 경로와 동일한 프롬프트를 build_director_prompt로 조립(형식 드리프트 방지)."""
    import copy as _c
    from app.gateway.design.directing import build_director_prompt
    spec = _c.deepcopy(F.LAYOUT_SPEC)
    for s in spec["slots"]:
        if s["role"] == "headline":
            s["color"], s["font_px"] = headline_color, headline_px
    spec["copy"] = {lang: dict(copy_map)}
    facts = {"금리": "연 3.5%", "만기": "12개월"}
    return build_director_prompt(spec, {}, facts, ["연 3.5%", "12개월 만기"], lang)


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
    # 비ko clean 카피도 상태 매칭(2026-07-04 언어 변형 fixture) — 파일 유무는 로더가 가른다.
    assert _poster_state(dict(F.COPY["en"]), gold_prompt) == "v2"
    assert _poster_state(dict(F.COPY["vi"]), "") == "final"
    # 미지 카피(임의 편집) → None → PIL 폴백(AC 5)
    assert _poster_state({"headline": "임의로 편집된 헤드라인"}, "") is None
    assert _poster_state({}, "") is None


def test_poster_lang_detection():
    """헤드라인 정확 일치로 언어 판별 — 미지/ko는 ko."""
    from app.providers.demo import _poster_lang
    assert _poster_lang(dict(F.COPY["en"])) == "en"
    assert _poster_lang(dict(F.COPY["vi"])) == "vi"
    assert _poster_lang(dict(F.COPY["zh"])) == "zh"
    assert _poster_lang(dict(F.COPY["ko"])) == "ko"
    assert _poster_lang({"headline": "임의"}) == "ko"
    assert _poster_lang({}) == "ko"


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


def test_load_poster_fixture_lang_variants(tmp_path, monkeypatch):
    """비ko는 poster_{state}_{lang}.png — 없는 조합·미지 언어는 None(PIL 폴백 경로)."""
    (tmp_path / "poster_v2_en.png").write_bytes(F.placeholder_png(64, 80))
    monkeypatch.setattr(F, "_POSTER_DIR", str(tmp_path))
    png = F.load_poster_fixture("v2", "en")
    assert png and png[:8] == b"\x89PNG\r\n\x1a\n"
    assert F.load_poster_fixture("final", "en") is None   # 파일 부재 → None
    assert F.load_poster_fixture("v2", "jp") is None      # 미지 언어 → None


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


def test_generate_image_lang_variant_returns_lang_fixture(tmp_path, monkeypatch):
    """비ko 골드 베이크 프롬프트(실 directed 산출) → 해당 언어 v2 fixture 바이트 그대로."""
    from app.providers.demo import DemoProvider
    (tmp_path / "poster_v2_vi.png").write_bytes(F.placeholder_png(64, 80))
    monkeypatch.setattr(F, "_POSTER_DIR", str(tmp_path))
    expected = F.load_poster_fixture("v2", "vi")
    prompt = _directed_prompt(F.COPY["vi"], headline_color="#FFD166",
                              headline_px=88, lang="vi")
    assert DemoProvider().generate_image(prompt, aspect="4:5") == expected


def test_generate_image_falls_back_to_pil_when_no_fixture(tmp_path, monkeypatch):
    """fixture 파일 부재 시 현행 PIL 베이크 폴백 — 완주 보장(AC 5). 배경 원본과 달라야 한다."""
    from app.providers.demo import DemoProvider
    monkeypatch.setattr(F, "_POSTER_DIR", str(tmp_path))   # 빈 디렉토리 = fixture 전무
    prompt = "컨셉\n- headline: 연 3.5% JB 정기예금\n- body: 12개월 만기\n- cta: 가입"
    png = DemoProvider().generate_image(prompt, aspect="4:5")
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert png != F.load_poster_bg()   # 카피가 합성됨(맨 배경 아님)


def test_poster_fixture_files_are_valid():
    """커밋된 실생성 fixture 5종 — PNG·10MB 미만·4:5(±3%) 검증(AC 4 자산 근거)."""
    import io
    import os

    from PIL import Image

    from app.providers.demo_fixtures import _POSTER_DIR, POSTER_STATES
    names = [f"poster_{s}.png" for s in POSTER_STATES] + ["poster_bg.png"]
    # 언어 변형(2026-07-04, 사용자 제작 — v2 베이스 텍스트 교체본)
    names += [f"poster_v2_{lg}.png" for lg in ("en", "vi", "zh")]
    for name in names:
        path = os.path.join(_POSTER_DIR, name)
        assert os.path.exists(path), f"{name} 누락 — scripts/gen_demo_posters.py로 생성"
        with open(path, "rb") as f:
            data = f.read()
        assert data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) < 10 * 1024 * 1024, name
        im = Image.open(io.BytesIO(data))
        assert abs(im.width / im.height - 0.8) < 0.03, f"{name} 비율 {im.width}x{im.height} ≠ 4:5"


# --- 언어 변형 단계 상속(2026-07-05 GAP): 입력 이미지 패밀리로 위반/교정 단계를 가른다 ---

def test_poster_family_of_matches_ko_fixture_bytes(tmp_path, monkeypatch):
    """입력 이미지가 ko fixture와 바이트 일치하면 그 상태 패밀리를 돌려준다."""
    _seed_fixture_dir(tmp_path, monkeypatch, states=("violating_gold",))
    monkeypatch.setattr(F, "_POSTER_HASHES", None)   # 해시 캐시 리셋
    vg = F.load_poster_fixture("violating_gold")
    assert F.poster_family_of(vg) == "violating_gold"
    assert F.poster_family_of(b"not-a-fixture") is None
    assert F.poster_family_of(None) is None


def test_lang_variant_inherits_family_from_input_image(tmp_path, monkeypatch):
    """교정 전(위반 골드) 주 언어 포스터로 만드는 비ko 변형이 v2(교정본) fixture로
    새면 안 된다 — 비ko 카피는 위반·교정 양쪽 clean이라 카피만으론 단계를 못 가른다."""
    from app.providers.demo import DemoProvider
    (tmp_path / "poster_violating_gold.png").write_bytes(F.placeholder_png(64, 80))
    (tmp_path / "poster_v2_vi.png").write_bytes(F.placeholder_png(96, 120))
    monkeypatch.setattr(F, "_POSTER_DIR", str(tmp_path))
    monkeypatch.setattr(F, "_POSTER_HASHES", None)
    vg = F.load_poster_fixture("violating_gold")
    prompt = _directed_prompt(F.COPY["vi"], headline_color="#FFD166",
                              headline_px=88, lang="vi")
    out = DemoProvider().generate_image(prompt, aspect="4:5", image=vg)
    assert out != F.load_poster_fixture("v2", "vi")   # 교정본 오노출 금지
    # violating_gold_{lang} fixture가 생기면 그것을 사용(로더 네이밍 규약).
    (tmp_path / "poster_violating_gold_vi.png").write_bytes(F.placeholder_png(48, 60))
    out2 = DemoProvider().generate_image(prompt, aspect="4:5", image=vg)
    assert out2 == F.load_poster_fixture("violating_gold", "vi")


def test_lang_variant_post_fix_keeps_v2_fixture(tmp_path, monkeypatch):
    """교정 후(v2) 주 언어 포스터 기반 변형은 현행대로 v2_{lang} fixture."""
    from app.providers.demo import DemoProvider
    (tmp_path / "poster_v2.png").write_bytes(F.placeholder_png(64, 80))
    (tmp_path / "poster_v2_vi.png").write_bytes(F.placeholder_png(96, 120))
    monkeypatch.setattr(F, "_POSTER_DIR", str(tmp_path))
    monkeypatch.setattr(F, "_POSTER_HASHES", None)
    v2 = F.load_poster_fixture("v2")
    prompt = _directed_prompt(F.COPY["vi"], headline_color="#FFD166",
                              headline_px=88, lang="vi")
    out = DemoProvider().generate_image(prompt, aspect="4:5", image=v2)
    assert out == F.load_poster_fixture("v2", "vi")


def test_layout_spec_v2_headline_is_calligraphy():
    """티키타카 spec의 헤드라인은 캘리그래피 스타일 힌트를 갖는다(프리뷰 렌더 신호)."""
    hl = next(s for s in F.LAYOUT_SPEC_V2["slots"] if s["role"] == "headline")
    assert hl.get("font_style") == "calligraphy"
    # V1은 스타일 힌트 없음(오염 가드)
    hl1 = next(s for s in F.LAYOUT_SPEC["slots"] if s["role"] == "headline")
    assert "font_style" not in hl1


# --- Stage A 디자인 디렉션 제안 턴(spec D4): image 매체 4턴 구조·video 3턴 불변 ---

def _stage_a_msgs(n_user_turns: int):
    from app.providers.base import Message
    msgs = []
    for i in range(n_user_turns):
        if i:
            msgs.append(Message("assistant", "질문"))
        msgs.append(Message("user", f"답변{i}"))
    return msgs


def test_stage_a_turn3_is_design_direction_proposal():
    """3턴(image) = AI 제안 턴 — 리서치 근거로 권장 디렉션 제시 + 옵션 논의(spec D4)."""
    from app.providers.demo import DemoProvider
    r = json.loads(DemoProvider().complete(
        _stage_a_msgs(3), model="demo",
        meta={"studio": "brainstorming", "step": "stage_a"}).text)
    assert r["ready"] is False and r["document"] == ""
    assert r["ask"]["trigger"] == "a"
    assert "권장" in "".join(r["ask"]["options"])       # 권장안이 옵션에 명시
    assert "#00857C" in r["reply"] and "골드" in r["reply"]   # 구체 제안(팔레트·포인트)


def test_stage_a_turn4_returns_spec_with_direction_ack():
    from app.providers.demo import DemoProvider
    r = json.loads(DemoProvider().complete(
        _stage_a_msgs(4), model="demo",
        meta={"studio": "brainstorming", "step": "stage_a"}).text)
    assert r["ready"] is True and "goal:" in r["document"]
    assert "디렉션" in r["reply"]                        # 선택 반영 acknowledgment


def test_stage_a_video_keeps_3turn_spec():
    """video 매체는 3턴째 spec 그대로(D4 medium 게이트·D6 영상 무변경)."""
    from app.providers.demo import DemoProvider
    r = json.loads(DemoProvider().complete(
        _stage_a_msgs(3), model="demo",
        meta={"studio": "brainstorming", "step": "stage_a", "medium": "video"}).text)
    assert r["ready"] is True and r["document"]


# --- Stage D 아티팩트급 spec/plan 본문 갱신(spec D5): 디자인 시스템 어휘 ---

def test_spec_and_plan_md_have_design_system_vocab():
    """D5 — 새 기능 어휘(타이포 위계·safe zone·2K·골드 포인트)가 spec/plan 본문에 존재."""
    for doc in (F.SPEC_MD, F.PLAN_MD):
        assert "타이포" in doc and "safe zone" in doc.lower() or "세이프존" in doc
    assert "2K" in F.PLAN_MD and "골드" in F.PLAN_MD


def test_plan_md_frontmatter_palette_has_no_gold():
    """골드 오염 가드 — frontmatter palette에 #FFD166 금지(Global Constraints).
    S0 tokens에 스며들면 directed 프롬프트에 골드가 상존해 2×2 골드 축이 오염된다."""
    fm_block = F.PLAN_MD.split("---")[1]
    assert "FFD166" not in fm_block


def test_layout_spec_v2_prestages_calli_headline_sample():
    """티키타카 spec은 캘리 헤드라인 견본(ko)을 프리스테이지 — 카피 전 프리뷰에 즉시 표시.
    V1 spec의 copy는 비어 있어야 한다(프리스테이지는 티키타카 전용)."""
    assert F.LAYOUT_SPEC_V2["copy"] == {"ko": {"headline": F.COPY["ko"]["headline"]}}
    assert F.LAYOUT_SPEC["copy"] == {}
