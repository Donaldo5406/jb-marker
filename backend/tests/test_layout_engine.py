from app.gateway.design.layout_engine import (
    DEFAULT_SEMANTIC, MOOD_FONTS, build_layout,
)

FACTS = {"상품명": "JB 20대 청년 정기예금", "기본금리": "연 2.80%",
         "최고금리": "최고 연 3.30%", "우대금리": "우대 최대 연 0.50%p",
         "가입기간": "6~36개월", "최소가입금액": "100만원"}
COPY = {"headline": "청춘의 저축", "body": "본문", "cta": "지금 가입하기"}
SEM = {"clear_zones": ["top-left"], "busy_zones": ["lower-third"],
       "palette": ["#0B1F3A", "#0066FF"], "mood": "youth"}


def _slots_by_role(out):
    return {s["role"]: s for s in out["slots"]}


def test_build_layout_emits_seam_contract_fields():
    out = build_layout(SEM, "4:5", COPY, FACTS)
    assert out["render_mode"] == "vector_chrome"
    by = _slots_by_role(out)
    # 필수 role 전부(logo는 S2c 소유라 없음)
    for role in ("headline", "body", "rate_card", "benefit_row", "cta_button", "disclosure"):
        assert role in by, role
    assert "logo" not in by
    h = by["headline"]
    assert h["font_family"] == "GmarketSansBold" and h["weight"] == 800
    assert h["copy_key"] == "headline" and h["color"] == "#0B1F3A"   # palette[0]
    rc = by["rate_card"]
    assert rc["container"]["fill"] == "#FFFFFF" and rc["container"]["radius"] == 16
    styles = [ln["style"] for ln in rc["lines"]]
    assert "figure" in styles and "label" in styles
    cta = by["cta_button"]
    assert cta["fill"] == "#0066FF" and cta["text_color"] == "#FFFFFF"  # palette[1]
    assert cta["copy_key"] == "cta" and cta["radius"] == 999


def test_grounding_no_invented_numbers():
    # slots 안의 모든 숫자 문자열은 facts 값(또는 그 연결)에서만 — 새 수치 창작 금지
    import re
    out = build_layout(SEM, "4:5", COPY, FACTS)
    fact_blob = " ".join(FACTS.values())
    for s in out["slots"]:
        for ln in s.get("lines", []):
            for num in re.findall(r"\d+(?:[.,]\d+)?", ln["text"]):
                assert num in fact_blob, f"invented number {num} in {ln['text']}"
        for it in s.get("items", []):
            for num in re.findall(r"\d+(?:[.,]\d+)?", it["title"] + it["desc"]):
                assert num in fact_blob, f"invented number {num}"


def test_benefit_icon_keys_in_frontend_allowlist():
    allow = {"trending-up", "calendar", "coins", "shield", "percent", "gift"}
    out = build_layout(SEM, "4:5", COPY, FACTS)
    items = _slots_by_role(out)["benefit_row"]["items"]
    assert items and all(it["icon_key"] in allow for it in items)


def test_mood_font_mapping_and_default():
    assert MOOD_FONTS["youth"][0] == "GmarketSansBold"
    assert MOOD_FONTS["premium"][0] == "NanumMyeongjo"
    assert MOOD_FONTS["campaign"][0] == "NanumPenScript"
    out = build_layout({**SEM, "mood": "unknown-mood"}, "4:5", COPY, FACTS)
    assert _slots_by_role(out)["headline"]["font_family"] == "Pretendard"  # 미지 mood 폴백


def test_vertical_stacking_no_overlap_both_aspects():
    for aspect, height in (("4:5", 1350), ("1:1", 1080)):
        out = build_layout(SEM, aspect, COPY, FACTS)
        by = _slots_by_role(out)
        order = ["headline", "body", "rate_card", "benefit_row", "cta_button", "disclosure"]
        ys = [by[r]["bbox"]["y"] for r in order]
        assert ys == sorted(ys), f"{aspect}: 스택 순서 붕괴 {ys}"
        for a, b in zip(order, order[1:]):
            assert by[a]["bbox"]["y"] + by[a]["bbox"]["h"] <= by[b]["bbox"]["y"], \
                f"{aspect}: {a}∩{b} 겹침"
        disc = by["disclosure"]["bbox"]
        assert disc["y"] + disc["h"] <= height   # 캔버스 안


def test_body_slot_only_when_copy_has_body():
    out = build_layout(SEM, "4:5", {"headline": "H", "cta": "C"}, FACTS)
    assert "body" not in _slots_by_role(out)


def test_default_semantic_fallback_produces_valid_layout():
    out = build_layout(DEFAULT_SEMANTIC, "1:1", COPY, FACTS)
    assert out["render_mode"] == "vector_chrome"
    assert _slots_by_role(out)["headline"]["color"]   # 팔레트 없어도 폴백 색


def test_deterministic():
    a = build_layout(SEM, "4:5", COPY, FACTS)
    b = build_layout(SEM, "4:5", COPY, FACTS)
    assert a == b
