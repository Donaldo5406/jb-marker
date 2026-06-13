from app.gateway.design.prompts import (
    PERSONA, S1_INSTR, S2A_VISION_INSTR,
)


def test_s1_instr_requires_visual_concept():
    # S1 출력 스키마에 visual_concept이 필수 필드로 명시되어야 한다
    assert "visual_concept" in S1_INSTR
    # 예시 JSON에도 visual_concept 키가 포함(LLM이 스키마를 따르도록)
    assert '"visual_concept"' in S1_INSTR


def test_persona_has_art_direction():
    # 키비주얼 아트디렉션 역량(인물·구도·조명 등)을 인코딩
    assert "키비주얼" in PERSONA
    # 레이어 분리 원칙은 보존
    assert "레이어" in PERSONA


def test_vision_instr_covers_three_checks():
    # 비전 게이트 프롬프트: 텍스트 누출·인물 결함·safe zone 3축 + JSON findings 계약
    for kw in ("글자", "손", "findings", "severity"):
        assert kw in S2A_VISION_INSTR
