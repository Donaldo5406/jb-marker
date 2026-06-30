"""영상 프롬프트/콘티 톤 가드 (video-studio realad spec §4).

추상 텍스처 → 실제 광고 시네마틱 씬으로의 업그레이드를 고정하고,
컴플라이언스 불변(텍스트-free·글자금지)을 회귀 방지한다.
"""
from app.gateway.video import prompts as vp
from app.providers.demo_fixtures import STORYBOARD_SPEC


def test_persona_directs_real_cinematic_ad():
    p = vp.PERSONA
    assert "광고" in p
    assert "시네마틱" in p
    # 규제 텍스트는 footage에 굽지 않고 레이어로 분리(컴플라이언스 불변)
    assert "레이어" in p


def test_v1_instr_directs_cinematic_scene_and_keeps_text_free():
    s = vp.V1_INSTR
    assert "시네마틱" in s            # 실광고 장면 지시
    assert "글자" in s               # no-text 가드(레이어 분리)
    assert "3초" in s                # disclosure >=3초 유지
    assert "추상" not in s           # 추상 배경 예시 제거됨


def test_v1_example_footage_is_concrete_scene():
    # JSON 예시의 footage_prompt가 구체 장면(인물/공간)을 담는다
    assert "카페" in vp.V1_INSTR


def test_v1_instr_steers_away_from_device_screens():
    # footgun 회귀 방지(실측 2026-06-30): 카메라 향한 기기 화면 → 깨진 가짜 UI 글씨.
    # V1_INSTR이 화면 회피/블랭크를 지시하는지 고정.
    s = vp.V1_INSTR
    assert "화면" in s


def test_demo_storyboard_footage_is_real_scene_and_text_free():
    shots = STORYBOARD_SPEC["shots"]
    assert len(shots) == 4
    for sh in shots:
        fp = sh["footage_prompt"]
        assert "추상" not in fp                     # 추상 톤 제거
        assert "텍스트 없음" in fp                   # 텍스트-free 마커 유지(컴플라이언스)
    # 적어도 한 샷은 구체적 인물/공간 장면을 담는다
    joined = " ".join(sh["footage_prompt"] for sh in shots)
    assert "카페" in joined or "거실" in joined or "직장인" in joined
