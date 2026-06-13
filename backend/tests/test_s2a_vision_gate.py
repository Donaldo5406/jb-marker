from app.gateway.design.prompts import (
    PERSONA, S1_INSTR, S2A_VISION_INSTR,
)

import json

import pytest

from app.gateway.harness_design import DesignHarness
from app.providers.base import ProviderResponse
from app.providers.fake import FakeProvider
from app.vfs.local import LocalVfsStore


def _store(tmp_path):
    s = LocalVfsStore(storage_dir=str(tmp_path))
    s.create_run("r1", languages=["ko"])
    s.put("/r1/brainstorming/plan.md",
          "---\ncreative_direction:\n  aspect: \"1:1\"\n"
          "factsheet:\n  rate: \"연 3.5%\"\n"
          "material_matrix: [{channel: instagram, lang: ko}]\nlanguages: [ko]\n---\n본문",
          source="marker", mime="text/markdown")
    return s


def _req(action="advance", prompt=""):
    from app.gateway.harness import HarnessRequest
    return HarnessRequest(run_id="r1", studio="design", user_prompt=prompt,
                          provider="fake", is_marker=True, action=action)


def _seed_s2a(s, bypass):
    # S2a에서 시작하도록 상태·레이아웃 시드(기존 test_design_gate 패턴)
    s.put("/r1/design/_state.json", json.dumps(
        {"step": "S2a", "gate": None, "confirmed": {}, "bypass": bypass,
         "languages": ["ko"]}), source="marker", mime="application/json")
    s.put("/r1/design/rough/layout.spec.json",
          json.dumps({"visual_concept": "통장 든 청년", "aspect": "1:1", "copy": {"ko": {}}}),
          source="marker", mime="application/json")


class _DirtyVision(FakeProvider):
    """generate_image 호출수를 세고, review_image로 critical finding을 반환."""
    def __init__(self):
        self.gen_calls = 0
    def generate_image(self, prompt, *, aspect="1:1"):
        self.gen_calls += 1
        return super().generate_image(prompt, aspect=aspect)
    def review_image(self, image_bytes, prompt, *, mime="image/png"):
        return ProviderResponse(
            text='{"findings":[{"severity":"critical","slot":"visual","evidence":"손가락 6개"}]}',
            model="fake")


class _NoVision(FakeProvider):
    """review_image 미지원(base NotImplementedError) — fail-open 확인용."""
    def review_image(self, image_bytes, prompt, *, mime="image/png"):
        raise NotImplementedError("vision 미지원")


def test_s2a_clean_vision_passes_gate_on(tmp_path):
    # FakeProvider review_image = {"findings":[]} → 게이트 ON에서 정지하되 critic.passed=True
    s = _store(tmp_path)
    _seed_s2a(s, bypass={})
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(), provider=FakeProvider(), store=s)
    assert res.gate.step == "S2a"
    assert res.gate.critic == {"passed": True, "issues": []}


def test_s2a_bypass_critical_regenerates_once(tmp_path):
    # S2a bypass + critical finding → 1회 자동 재생성(generate_image 2회)
    s = _store(tmp_path)
    _seed_s2a(s, bypass={"S2a": True})
    img = _DirtyVision()
    h = DesignHarness(image_provider=img)
    h.handle_turn(_req(), provider=FakeProvider(), store=s)
    assert img.gen_calls == 2


def test_s2a_vision_failure_is_fail_open(tmp_path):
    # review_image가 NotImplementedError → 게이트 통과 + critic passed True
    s = _store(tmp_path)
    _seed_s2a(s, bypass={})
    h = DesignHarness(image_provider=_NoVision())
    res = h.handle_turn(_req(), provider=FakeProvider(), store=s)
    assert res.gate.step == "S2a"
    assert res.gate.critic == {"passed": True, "issues": []}


def test_s1_instr_requires_visual_concept():
    # S1 출력 스키마에 visual_concept이 필수 필드로 명시되어야 한다
    assert "visual_concept" in S1_INSTR
    # 예시 JSON에도 visual_concept 키가 포함(LLM이 스키마를 따르도록)
    assert '"visual_concept"' in S1_INSTR


def test_persona_has_art_direction():
    # 키비주얼 아트디렉션 역량(인물·구도·조명 등)을 인코딩
    assert "키비주얼" in PERSONA
    # 원-레이어 베이크 반전: 텍스트 레이어 분리 원칙 제거, 통합 디자인으로 전환
    assert "레이어로 분리" not in PERSONA
    assert "통합 디자인" in PERSONA


def test_vision_instr_covers_three_checks():
    # 비전 게이트 프롬프트: 텍스트 누출·인물 결함·safe zone 3축 + JSON findings 계약
    for kw in ("글자", "손", "findings", "severity"):
        assert kw in S2A_VISION_INSTR


def test_prompts_inverted_for_onelayer_bake():
    from app.gateway.design import prompts as P
    # PERSONA·S1_INSTR에서 "텍스트 레이어 분리/금지" 제거
    assert "레이어로 분리" not in P.PERSONA
    assert "넣지 마세요" not in P.S1_INSTR and "텍스트 없음" not in P.S1_INSTR
    # 비전 지시문은 기대 카피를 받는 빌더 — 정확성 검증 의미
    instr = P.build_vision_instr({"headline": "청년 적금 5.00%", "cta": "지금 신청"})
    assert "청년 적금 5.00%" in instr          # 기대 카피 주입
    assert "일치" in instr and "critical" in instr
