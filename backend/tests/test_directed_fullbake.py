"""디렉티드 풀베이크(spec 2026-07-03 §4·§5) — DIRECTED_FULLBAKE flag.

핵심 계약:
- **flag off = 현행 `_bake_prompt` 바이트 동등**(최우선 케이스).
- flag on = 아트디렉터 풀디렉팅 프롬프트(카피 char-for-char·palette hex·safe zone 지시).
- disclosure 전문·로고 렌더 지시는 프롬프트에 **미포함**(E 실측 — 깨짐/근사).
- 존 번역(zone_label) 결정론.
- E2E(mock provider, flag on) S0→done 완주 + preview.html + v1.png.
"""
import json

import pytest

from app.core.parsing import parse_frontmatter
from app.gateway.design.directing import build_director_prompt, zone_label
from app.gateway.design.steps import (
    S2aVisual, _benefit_chips, _directed_enabled, _facts_from_factsheet, _facts_line,
)
from app.gateway.harness import HarnessRequest
from app.gateway.pipeline import StepContext
from app.providers.base import ProviderResponse
from app.providers.fake import FakeProvider
from app.vfs.local import LocalVfsStore

# disclosure 원문 부재 검증용 고유 마커(어떤 다른 섹션에도 안 나오는 문자열).
DISCLOSURE = "예금자보호법에 따라 5천만원까지 보호됩니다 ZQXW상세고지블록4줄"

SPEC = {
    "visual_concept": "밝은 채광의 카페 창가, 20대 청년이 환하게 미소짓는 상반신 화보",
    "aspect": "3:4",
    "slots": [
        {"role": "headline", "bbox": {"x": 80, "y": 120, "w": 920, "h": 180},
         "z": 3, "copy_key": "headline", "font_px": 96, "color": "#0B2D6B"},
        {"role": "body", "bbox": {"x": 80, "y": 520, "w": 900, "h": 120},
         "z": 2, "copy_key": "body", "font_px": 40, "color": "#1A2332"},
        {"role": "cta", "bbox": {"x": 80, "y": 1520, "w": 520, "h": 96},
         "z": 3, "copy_key": "cta", "font_px": 44, "color": "#FFFFFF"},
        {"role": "disclosure", "bbox": {"x": 80, "y": 1720, "w": 920, "h": 120},
         "z": 1, "copy_key": "disclosure", "font_px": 30, "color": "#3A3A3A"},
    ],
    "copy": {"ko": {
        "headline": "청년 정기예금으로 미래를 크게",
        "body": "연 3.30%, 100만원부터 시작하세요.",
        "cta": "지금 가입하기",
        "disclosure": DISCLOSURE,
    }},
}

PLAN = (
    "---\n"
    "factsheet:\n"
    '  interest_rate: "연 2.80%"\n'
    '  max_rate: "최고 연 3.30%"\n'
    '  prime_rate: "우대 최대 연 0.50%p"\n'
    '  term: "6~36개월"\n'
    '  min_amount: "100만원"\n'
    "languages: [ko]\n"
    "---\n본문\n"
)

TOKENS = {
    "palette": ["#0B2D6B", "#1F6BFF"],
    "aspect": "3:4",
    "typography": "굵은 모던 산세리프와 붓펜 캘리그래피의 대비",
    "visual_mood": "밝고 청량한 자연광",
}


class _CaptureProvider:
    """generate_image 프롬프트를 순서대로 기록 + review_image는 무결함(빈 findings)."""

    def __init__(self):
        self.gen_prompts = []

    def generate_image(self, prompt, *, aspect="1:1", image=None):
        self.gen_prompts.append(prompt)
        return b"\x89PNG\r\n\x1a\n\x00capture"

    def review_image(self, png, instr, *, mime="image/png"):
        return ProviderResponse(text='{"findings":[]}', model="m")


def _ctx(tmp_path):
    store = LocalVfsStore(storage_dir=str(tmp_path))
    store.create_run("r1", languages=["ko"])
    store.put("/r1/brainstorming/plan.md", PLAN, source="marker", mime="text/markdown")
    store.put("/r1/design/design-system/tokens.json", json.dumps(TOKENS, ensure_ascii=False),
              source="marker", mime="application/json")
    store.put("/r1/design/rough/layout.spec.json", json.dumps(SPEC, ensure_ascii=False),
              source="marker", mime="application/json")
    ctx = StepContext(req=HarnessRequest(run_id="r1", studio="design", user_prompt="",
                      provider="fake", is_marker=True), provider=None, store=store,
                      state={"languages": ["ko"]}, base="/r1/design")
    return store, ctx


def _facts():
    return _facts_from_factsheet(parse_frontmatter(PLAN).get("factsheet") or {})


# ── flag 파서 ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("val,on", [("1", True), ("true", True), ("TRUE", True),
                                    ("on", True), ("yes", True),
                                    ("0", False), ("", False), ("off", False)])
def test_directed_enabled_parses_truthy(monkeypatch, val, on):
    monkeypatch.setenv("DIRECTED_FULLBAKE", val)
    assert _directed_enabled() is on


def test_directed_disabled_when_unset(monkeypatch):
    monkeypatch.delenv("DIRECTED_FULLBAKE", raising=False)
    assert _directed_enabled() is False


# ── 최우선: flag off = _bake_prompt 바이트 동등 ─────────────────────────────

def test_flag_off_byte_identical_to_bake_prompt(tmp_path, monkeypatch):
    """DIRECTED_FULLBAKE off(+rich off)면 S2a가 넘기는 베이크 프롬프트가 현행
    `_bake_prompt` 결과와 **바이트 동등**해야 한다(회귀 하드락)."""
    monkeypatch.delenv("DIRECTED_FULLBAKE", raising=False)
    monkeypatch.delenv("RICH_VECTOR_CHROME", raising=False)
    stub = _CaptureProvider()
    store, ctx = _ctx(tmp_path)
    S2aVisual(stub).run(ctx)

    captured = stub.gen_prompts[0]              # _bake_with_retry 1차 = base_prompt 그대로
    facts = _facts()
    expected = S2aVisual(stub)._bake_prompt(
        SPEC["visual_concept"], SPEC["copy"]["ko"], SPEC["slots"],
        _facts_line(facts), _benefit_chips(facts))
    assert captured == expected                 # 바이트 동등
    assert "아트디렉터" not in captured          # directed 프롬프트로 새지 않음


# ── flag on: directed 프롬프트 내용 계약 ────────────────────────────────────

def test_directed_prompt_includes_copy_palette_and_safezones():
    facts = _facts()
    p = build_director_prompt(SPEC, TOKENS, facts, _benefit_chips(facts), "ko")
    assert "아트디렉터" in p
    assert SPEC["copy"]["ko"]["headline"] in p          # 헤드라인 char-for-char
    assert SPEC["copy"]["ko"]["cta"] in p               # CTA char-for-char
    assert "#0B2D6B" in p and "#1F6BFF" in p            # palette hex 명시
    assert "좌상단" in p and "하단" in p                 # 로고/고지 safe zone 지시
    assert "최고 연 3.30%" in p                          # 금리 카드 = facts 수치


def test_directed_prompt_excludes_disclosure_fulltext():
    """E 실측: disclosure 전문·조밀 고지는 프롬프트에 절대 미포함(베이크 시 깨짐)."""
    facts = _facts()
    p = build_director_prompt(SPEC, TOKENS, facts, _benefit_chips(facts), "ko")
    assert DISCLOSURE not in p
    assert "ZQXW상세고지블록4줄" not in p


def test_directed_prompt_has_no_logo_render_instruction():
    """로고는 결정론 오버레이(S2c) 담당 — 베이크 지시(사용·재그리기) 금지."""
    facts = _facts()
    p = build_director_prompt(SPEC, TOKENS, facts, _benefit_chips(facts), "ko")
    assert "로고를 사용" not in p
    assert "로고를 원본" not in p
    assert "로고를 그대로" not in p
    assert "첨부된 로고" not in p
    assert "로고" in p                                   # safe zone 문맥에서는 언급됨


def test_directed_prompt_benefit_chips_labels_verbatim():
    facts = _facts()
    chips = _benefit_chips(facts)
    assert chips                                         # factsheet에서 칩이 나와야 유의미
    p = build_director_prompt(SPEC, TOKENS, facts, chips, "ko")
    for c in chips:
        assert c in p                                    # 라벨 글자 그대로


def test_directed_prompt_deterministic():
    facts = _facts()
    chips = _benefit_chips(facts)
    a = build_director_prompt(SPEC, TOKENS, facts, chips, "ko")
    b = build_director_prompt(SPEC, TOKENS, facts, chips, "ko")
    assert a == b                                        # 순수·결정론


def test_directed_prompt_handles_empty_inputs():
    """방어: spec/tokens/facts/chips가 비어도 크래시 없이 유효 프롬프트."""
    p = build_director_prompt({}, {}, {}, [], "ko")
    assert isinstance(p, str) and "아트디렉터" in p and "좌상단" in p


# ── 존 번역(zone_label) 결정론 + 경계값 ─────────────────────────────────────

def test_zone_label_deterministic():
    bbox = {"x": 80, "y": 120, "w": 920, "h": 180}
    assert zone_label(bbox, "3:4") == zone_label(bbox, "3:4")   # 같은 입력 → 같은 라벨


def test_zone_label_vertical_boundary_0_33H():
    """3:4 → W=1080,H=1440. 0.33H=475.2 경계: 아래=상단, 위=중단(결정론)."""
    W, H = 1080, 1440
    assert zone_label({"x": 0, "y": 470, "w": 100, "h": 10}, "3:4").startswith("상단")
    assert zone_label({"x": 0, "y": 480, "w": 100, "h": 10}, "3:4").startswith("중단")


def test_zone_label_horizontal_by_center():
    """x 중심 기준 좌/중/우. 3:4 W=1080 → <356=좌측, <712=중앙, 그 외=우측."""
    assert zone_label({"x": 0, "y": 0, "w": 200, "h": 10}, "3:4").endswith("좌측")     # cx=100
    assert zone_label({"x": 440, "y": 0, "w": 200, "h": 10}, "3:4").endswith("중앙")   # cx=540
    assert zone_label({"x": 880, "y": 0, "w": 200, "h": 10}, "3:4").endswith("우측")   # cx=980


def test_zone_label_lower_third_is_bottom():
    # disclosure류 하단 슬롯(y=H-150)은 하단으로.
    assert zone_label({"x": 80, "y": 1290, "w": 920, "h": 110}, "3:4").startswith("하단")


# ── flag on 배선: run이 directed 프롬프트로 교체(baked 미사용) ───────────────

def test_flag_on_run_swaps_to_directed_prompt(tmp_path, monkeypatch):
    monkeypatch.setenv("DIRECTED_FULLBAKE", "1")
    monkeypatch.delenv("RICH_VECTOR_CHROME", raising=False)
    stub = _CaptureProvider()
    store, ctx = _ctx(tmp_path)
    S2aVisual(stub).run(ctx)
    p = stub.gen_prompts[0]
    assert "아트디렉터" in p                               # directed 프롬프트
    assert SPEC["copy"]["ko"]["headline"] in p
    assert "#0B2D6B" in p
    assert "다음 문구를 디자인 요소로" not in p             # 현행 _bake_prompt 문구 미사용
    # v1.png 저장은 두 경로 공통(directed는 프롬프트만 교체) — 후속 로직 공유 확인.
    assert store.get("/r1/design/design-system/components/visual/v1.png") is not None


def test_rich_takes_priority_over_directed(tmp_path, monkeypatch):
    """두 flag 동시 on이면 rich가 우선(분기 순서) — directed 프롬프트는 안 쓰임."""
    monkeypatch.setenv("DIRECTED_FULLBAKE", "1")
    monkeypatch.setenv("RICH_VECTOR_CHROME", "1")

    class _RichStub(_CaptureProvider):
        def review_image(self, png, instr, *, mime="image/png"):
            if "clear_zones" in instr:
                return ProviderResponse(
                    text='{"clear_zones":["top-left"],"busy_zones":[],'
                         '"palette":["#0B2D6B","#1F6BFF"],"mood":"youth"}', model="m")
            return ProviderResponse(text='{"findings":[]}', model="m")

    stub = _RichStub()
    store, ctx = _ctx(tmp_path)
    S2aVisual(stub).run(ctx)
    p = stub.gen_prompts[0]
    assert "아트디렉터" not in p                            # 텍스트프리 히어로(directed 아님)
    spec = json.loads(store.get("/r1/design/rough/layout.spec.json").content_text)
    assert spec.get("render_mode") == "vector_chrome"     # rich 경로


# ── E2E: flag-on 전체 파이프라인 완주 + preview.html + v1.png ────────────────

PLAN_E2E = (
    "---\n"
    "creative_direction:\n"
    '  aspect: "3:4"\n'
    '  palette: ["#0B2D6B", "#1F6BFF"]\n'
    '  typography: "굵은 모던 산세리프"\n'
    '  visual_mood: "밝고 청량한 자연광"\n'
    "factsheet:\n"
    '  interest_rate: "연 2.80%"\n'
    '  max_rate: "최고 연 3.30%"\n'
    '  prime_rate: "우대 최대 연 0.50%p"\n'
    '  term: "6~36개월"\n'
    '  min_amount: "100만원"\n'
    "disclosures:\n"
    '  - "예금자보호법에 따라 5천만원까지 보호"\n'
    "material_matrix: [{channel: instagram, lang: ko}]\n"
    "languages: [ko]\n"
    "---\n본문\n"
)


def test_e2e_pipeline_directed_flag_on(tmp_path, monkeypatch):
    """S0→…→done 완주(mock provider, DIRECTED_FULLBAKE on): preview.html + v1.png 산출.

    directed는 프롬프트만 교체하고 이후 로직(저장·다국어·vision cache)을 baked와 공유하므로
    전 파이프라인이 정상 완주해야 한다(bypass_map으로 전 gated step OFF → 한 턴 연쇄)."""
    monkeypatch.setenv("DIRECTED_FULLBAKE", "1")
    monkeypatch.delenv("RICH_VECTOR_CHROME", raising=False)
    from app.gateway.harness_design import DesignHarness

    store = LocalVfsStore(storage_dir=str(tmp_path))
    store.create_run("r1", languages=["ko"])
    store.put("/r1/brainstorming/plan.md", PLAN_E2E, source="marker", mime="text/markdown")

    h = DesignHarness(image_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="design", user_prompt="포스터",
                         provider="fake", is_marker=True, action="advance",
                         bypass_map={"S1": True, "S2b": True, "S2a": True,
                                     "S2c": True, "S3": True})
    res = h.handle_turn(req, provider=FakeProvider(), store=store)

    assert res.meta.get("step") == "done"                                 # 완주
    assert store.get("/r1/design/rough/preview.html") is not None         # 시안 프리뷰 노드
    assert store.get("/r1/design/design-system/components/visual/v1.png") is not None
