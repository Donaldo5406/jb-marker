from app.gateway.design.prompts import (
    PERSONA, S1_INSTR, S2A_VISION_INSTR,
)

import json

import pytest

from app.gateway.harness_design import DesignHarness
from app.providers.base import ProviderResponse
from app.providers.fake import FakeProvider
from app.vfs.local import LocalVfsStore


def test_bake_prompt_forbids_incidental_text():
    # footgun 회귀 방지(실측 2026-06-30): 모델이 폰 화면·간판·빈 영역에 깨진 잔글씨나
    # 'LOGO' placeholder를 굽는다. _bake_prompt가 명시 카피 외 텍스트를 금지하는지 고정.
    from app.gateway.design.steps import S2aVisual
    p = S2aVisual(None)._bake_prompt("카페 장면", {"headline": "안녕", "cta": "지금"})
    assert "안녕" in p and "지금" in p          # 명시 카피는 렌더
    assert "화면" in p                          # 기기 화면 블랭크 지시
    assert "가짜 잔글씨" in p                    # 부수 텍스트 금지
    assert "광고 수준" in p and "스톡" in p       # C2 아트디렉션 플로어(광고급 마감 하한)


def test_benefit_chips_grounded_only():
    # 혜택 칩 라벨은 factsheet 값에서만 파생(창작 금지) — 밀도 격차 해소 + 환각 차단.
    from app.gateway.design.steps import _benefit_chips
    facts = {"기본금리": "연 2.80%", "최고금리": "연 3.30%", "우대금리": "0.50%p",
             "가입기간": "6~36개월", "최소가입금액": "100만원"}
    chips = _benefit_chips(facts)
    assert chips == ["우대금리 0.50%p", "가입기간 6~36개월", "100만원부터"]
    assert _benefit_chips({}) == []          # facts 없으면 칩 없음(중복·환각 회피)
    # 값이 이미 '우대'/'부터'를 포함하면 접두·접미 중복 생략(실측 교정: '우대금리 우대…').
    dup = _benefit_chips({"우대금리": "우대 최대 연 0.50%p", "최소가입금액": "100만원부터"})
    assert dup == ["우대 최대 연 0.50%p", "100만원부터"]


def test_bake_prompt_includes_grounded_chip_row():
    # 칩이 있으면 베이크 프롬프트에 아이콘 칩 행 지시 + 그라운딩 라벨을 정확히 주입,
    # 없으면(기본) 칩 행 지시 없음(단일 언어·factsheet 결여 회귀 방지).
    from app.gateway.design.steps import S2aVisual
    v = S2aVisual(None)
    p = v._bake_prompt("카페 장면", {"headline": "안녕"},
                       chips=["우대금리 0.50%p", "가입기간 6~36개월"])
    assert "혜택 아이콘 칩 행" in p and "픽토그램" in p
    assert "우대금리 0.50%p" in p and "가입기간 6~36개월" in p
    assert "정확히 그대로만" in p              # 창작 금지(그라운딩 고정)
    assert "혜택 아이콘 칩 행" not in v._bake_prompt("카페 장면", {"headline": "안녕"})


def test_vision_gate_flags_prop_garbled_text():
    # C4: 소품·기기 화면의 깨진 잔글씨/임의 LOGO를 critical로 잡는지(베이크 footgun 이중방어)
    assert "잔글씨" in S2A_VISION_INSTR and "LOGO" in S2A_VISION_INSTR
    assert "critical" in S2A_VISION_INSTR


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
    def generate_image(self, prompt, *, aspect="1:1", image=None):
        self.gen_calls += 1
        return super().generate_image(prompt, aspect=aspect, image=image)
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
    # S2a bypass + 상시 critical → 내부 베이크 루프(run당 MAX_BAKE_ATTEMPTS회)와
    # 외부 게이트 1회 재생성이 합성: run 2회 × 내부 MAX_BAKE_ATTEMPTS회 = 4회.
    from app.gateway.design.steps import MAX_BAKE_ATTEMPTS
    s = _store(tmp_path)
    _seed_s2a(s, bypass={"S2a": True})
    img = _DirtyVision()
    h = DesignHarness(image_provider=img)
    h.handle_turn(_req(), provider=FakeProvider(), store=s)
    assert img.gen_calls == MAX_BAKE_ATTEMPTS * 2


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


def test_s2a_bake_retries_with_corrective_feedback(tmp_path):
    """1차 비전 실패(critical) → 2차 재생성, 2차 프롬프트에 교정 피드백 주입."""
    import json
    from app.gateway.design.steps import S2aVisual, MAX_BAKE_ATTEMPTS
    from app.gateway.pipeline import StepContext
    from app.gateway.harness import HarnessRequest
    from app.providers.base import ProviderResponse
    from app.vfs.local import LocalVfsStore

    class _Stub:
        def __init__(self):
            self.gen_prompts = []
            self._reviews = [
                '{"findings":[{"severity":"critical","slot":"visual","evidence":"헤드라인 깨짐"}]}',
                '{"findings":[]}',
            ]
        def generate_image(self, prompt, *, aspect="1:1", image=None):
            self.gen_prompts.append(prompt); return b"PNG"
        def review_image(self, png, instr, *, mime="image/png"):
            return ProviderResponse(text=self._reviews[len(self.gen_prompts) - 1], model="m")

    store = LocalVfsStore(storage_dir=str(tmp_path)); store.create_run("r1", languages=["ko"])
    store.put("/r1/design/rough/layout.spec.json", json.dumps({
        "visual_concept": "통장 든 청년", "aspect": "1:1", "bg_color": "#EEE",
        "copy": {"ko": {"headline": "청년 적금 5.00%", "cta": "지금 신청"}}}),
        source="marker", mime="application/json")
    stub = _Stub()
    ctx = StepContext(req=HarnessRequest(run_id="r1", studio="design", user_prompt="",
                      provider="fake", is_marker=True),
                      provider=None, store=store, state={"languages": ["ko"]},
                      base="/r1/design")
    S2aVisual(stub).run(ctx)
    assert len(stub.gen_prompts) == 2                       # 1차 실패 → 2차 재생성
    assert len(stub.gen_prompts) <= MAX_BAKE_ATTEMPTS
    assert "청년 적금 5.00%" in stub.gen_prompts[0]          # 기대 카피가 베이크 프롬프트에
    assert "헤드라인 깨짐" in stub.gen_prompts[1]            # 2차에 교정 피드백 주입


def test_s2a_multilang_image_edit_variants(tmp_path):
    """추가 언어는 주 언어 PNG를 입력으로 image-edit; visual_by_lang에 경로 기록.
    단일 언어면 변형 0회."""
    import json
    from app.gateway.design.steps import S2aVisual
    from app.gateway.pipeline import StepContext
    from app.gateway.harness import HarnessRequest
    from app.providers.base import ProviderResponse
    from app.vfs.local import LocalVfsStore

    class _Stub:
        def __init__(self): self.calls = []
        def generate_image(self, prompt, *, aspect="1:1", image=None):
            self.calls.append({"prompt": prompt, "image": image}); return b"PNG-" + (image or b"NEW")
        def review_image(self, png, instr, *, mime="image/png"):
            return ProviderResponse(text='{"findings":[]}', model="m")

    def _run(langs):
        store = LocalVfsStore(storage_dir=str(tmp_path / "_".join(langs)))
        store.create_run("r1", languages=langs)
        store.put("/r1/design/rough/layout.spec.json", json.dumps({
            "visual_concept": "통장 든 청년", "aspect": "1:1",
            "copy": {l: {"headline": f"H-{l}", "cta": f"C-{l}"} for l in langs}}),
            source="marker", mime="application/json")
        stub = _Stub()
        ctx = StepContext(req=HarnessRequest(run_id="r1", studio="design", user_prompt="",
                          provider="fake", is_marker=True), provider=None, store=store,
                          state={"languages": langs}, base="/r1/design")
        S2aVisual(stub).run(ctx)
        spec = json.loads(store.get("/r1/design/rough/layout.spec.json").content_text)
        return stub, spec

    # 단일 언어: 변형 없음(생성 1회 이상이나 전부 image=None)
    stub1, spec1 = _run(["ko"])
    assert all(c["image"] is None for c in stub1.calls)
    assert set(spec1["visual_by_lang"]) == {"ko"}

    # 다국어: en 변형이 ko PNG를 image로 받음
    stub2, spec2 = _run(["ko", "en"])
    edits = [c for c in stub2.calls if c["image"] is not None]
    assert len(edits) == 1 and edits[0]["image"] == b"PNG-NEW"   # 주 언어 베이크 결과를 입력
    assert set(spec2["visual_by_lang"]) == {"ko", "en"}
