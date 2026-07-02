from app.gateway.design.prompts import (
    SEMANTIC_LAYOUT_INSTR, TEXTFREE_VISION_INSTR, build_hero_prompt,
)


def test_hero_prompt_forbids_all_text_and_keeps_art_floor():
    p = build_hero_prompt("도심 카페의 청년", "생기, 낙관")
    assert "도심 카페의 청년" in p
    assert "텍스트" in p and "금지" in p            # 전면 텍스트 금지
    assert "네거티브 스페이스" in p or "여백" in p   # 벡터 텍스트 얹을 공간
    assert "광고" in p                              # 아트디렉션 플로어 유지
    assert "좌상단" in p and "하단" in p            # 로고/고지 세이프존 유지


def test_semantic_layout_instr_contract():
    for key in ("clear_zones", "busy_zones", "palette", "mood"):
        assert key in SEMANTIC_LAYOUT_INSTR
    assert "youth" in SEMANTIC_LAYOUT_INSTR and "premium" in SEMANTIC_LAYOUT_INSTR
    assert "픽셀" in SEMANTIC_LAYOUT_INSTR          # 픽셀 좌표 금지 명시
    assert "JSON" in SEMANTIC_LAYOUT_INSTR


def test_textfree_vision_gate_flags_any_text():
    assert "critical" in TEXTFREE_VISION_INSTR
    assert "글자" in TEXTFREE_VISION_INSTR or "텍스트" in TEXTFREE_VISION_INSTR
    assert "findings" in TEXTFREE_VISION_INSTR
