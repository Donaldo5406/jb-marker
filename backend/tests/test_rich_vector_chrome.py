import json

import pytest

from app.gateway.design.prompts import (
    SEMANTIC_LAYOUT_INSTR, TEXTFREE_VISION_INSTR, build_hero_prompt,
)
from app.gateway.design.steps import S2aVisual
from app.gateway.harness import HarnessRequest
from app.gateway.pipeline import StepContext
from app.providers.base import ProviderResponse
from app.vfs.local import LocalVfsStore


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


# ── rich 분기 배선 테스트(Task 3) ──────────────────────────────────────────

SEM_JSON = ('{"clear_zones":["top-left"],"busy_zones":[],'
            '"palette":["#0B1F3A","#0066FF"],"mood":"youth"}')


class _RichStub:
    """generate_image 프롬프트 기록 + review_image가 텍스트프리 게이트→의미 레이아웃 순으로 응답."""
    def __init__(self, layout_json=SEM_JSON):
        self.gen_prompts, self.review_instrs = [], []
        self._layout_json = layout_json
    def generate_image(self, prompt, *, aspect="1:1", image=None, image_size=None):
        self.gen_prompts.append({"prompt": prompt, "image": image}); return b"PNG"
    def review_image(self, png, instr, *, mime="image/png"):
        self.review_instrs.append(instr)
        if "의미 레이아웃" in instr or "clear_zones" in instr:
            return ProviderResponse(text=self._layout_json, model="m")
        return ProviderResponse(text='{"findings":[]}', model="m")


def _ctx(tmp_path, langs=("ko",)):
    store = LocalVfsStore(storage_dir=str(tmp_path)); store.create_run("r1", languages=list(langs))
    store.put("/r1/brainstorming/plan.md",
              "---\nfactsheet:\n  interest_rate: \"연 2.80%\"\n  max_rate: \"최고 연 3.30%\"\n"
              "  term: \"6~36개월\"\n  min_amount: \"100만원\"\nlanguages: [" + ", ".join(langs) + "]\n---\n",
              source="marker", mime="text/markdown")
    store.put("/r1/design/rough/layout.spec.json", json.dumps({
        "visual_concept": "도심 카페의 청년", "aspect": "4:5",
        "copy": {l: {"headline": f"H-{l}", "body": "B", "cta": f"C-{l}"} for l in langs}}),
        source="marker", mime="application/json")
    return store, StepContext(req=HarnessRequest(run_id="r1", studio="design", user_prompt="",
                              provider="fake", is_marker=True), provider=None, store=store,
                              state={"languages": list(langs)}, base="/r1/design")


def test_flag_off_keeps_baked_path(tmp_path, monkeypatch):
    monkeypatch.delenv("RICH_VECTOR_CHROME", raising=False)
    stub = _RichStub(); store, ctx = _ctx(tmp_path)
    S2aVisual(stub).run(ctx)
    assert "정확히" in stub.gen_prompts[0]["prompt"]       # 베이크 지시 유지
    spec = json.loads(store.get("/r1/design/rough/layout.spec.json").content_text)
    assert "render_mode" not in spec                        # 현행 그대로


def test_flag_on_generates_textfree_hero_and_vector_spec(tmp_path, monkeypatch):
    monkeypatch.setenv("RICH_VECTOR_CHROME", "1")
    stub = _RichStub(); store, ctx = _ctx(tmp_path)
    S2aVisual(stub).run(ctx)
    p = stub.gen_prompts[0]["prompt"]
    assert "금지" in p and "H-ko" not in p                  # 텍스트 프리(카피 미주입)
    spec = json.loads(store.get("/r1/design/rough/layout.spec.json").content_text)
    assert spec["render_mode"] == "vector_chrome"
    roles = {s["role"] for s in spec["slots"]}
    assert {"headline", "rate_card", "benefit_row", "cta_button", "disclosure"} <= roles
    assert spec["copy"]["ko"]["headline"] == "H-ko"         # copy 보존
    assert spec["aspect"] == "4:5"                          # 나머지 보존


def test_flag_on_multilang_no_edit_variants(tmp_path, monkeypatch):
    monkeypatch.setenv("RICH_VECTOR_CHROME", "1")
    stub = _RichStub(); store, ctx = _ctx(tmp_path, langs=("ko", "en"))
    S2aVisual(stub).run(ctx)
    assert all(g["image"] is None for g in stub.gen_prompts)   # image-edit 0회
    spec = json.loads(store.get("/r1/design/rough/layout.spec.json").content_text)
    assert spec["visual_by_lang"]["ko"] == spec["visual_by_lang"]["en"]  # 같은 히어로


def test_flag_on_vision_junk_falls_back_to_default_semantic(tmp_path, monkeypatch):
    monkeypatch.setenv("RICH_VECTOR_CHROME", "1")
    stub = _RichStub(layout_json="NOT-JSON")   # 의미 레이아웃 파싱 불가 → 폴백
    store, ctx = _ctx(tmp_path)
    S2aVisual(stub).run(ctx)                    # 죽지 않고
    spec = json.loads(store.get("/r1/design/rough/layout.spec.json").content_text)
    assert spec["render_mode"] == "vector_chrome"   # 폴백 레이아웃으로 완주


# ── C1 회귀: rich slots 교체가 히어로 background 슬롯을 방출(생성/보존)해야 한다 ──


def test_flag_on_creates_background_slot_for_hero(tmp_path, monkeypatch):
    """C1: engine slots가 background를 방출하지 않으므로 rich가 생성해 앞에 붙여야 한다.
    프론트(assembleScenes)는 role==background 슬롯으로만 히어로를 그린다(없으면 흰 캔버스)."""
    monkeypatch.setenv("RICH_VECTOR_CHROME", "1")
    stub = _RichStub(); store, ctx = _ctx(tmp_path)   # 기본 spec엔 background 없음
    S2aVisual(stub).run(ctx)
    spec = json.loads(store.get("/r1/design/rough/layout.spec.json").content_text)
    assert spec["slots"][0]["role"] == "background"           # 맨 앞에 히어로 슬롯
    bg = spec["slots"][0]
    assert bg["asset_ref"] == "design-system/components/visual/v1.png"   # 폴백 asset_ref
    assert bg["bbox"]["w"] == 1080 and bg["bbox"]["h"] == 1350           # 4:5 → 1080×1350


def test_flag_on_preserves_existing_background_and_logo_slots(tmp_path, monkeypatch):
    """C1 + belt-and-suspenders: 기존 background(커스텀 asset_ref)와 logo 슬롯은
    slots 교체(prepend/append) 시 보존된다 — engine 벡터 슬롯과 공존."""
    monkeypatch.setenv("RICH_VECTOR_CHROME", "1")
    stub = _RichStub(); store, ctx = _ctx(tmp_path)
    spec0 = json.loads(store.get("/r1/design/rough/layout.spec.json").content_text)
    spec0["slots"] = [
        {"role": "background", "z": 0, "asset_ref": "custom/hero.png",
         "bbox": {"x": 0, "y": 0, "w": 1080, "h": 1350}},
        {"role": "logo", "z": 9, "asset_ref": "design-system/components/logo/v1.png",
         "bbox": {"x": 48, "y": 48, "w": 300, "h": 96}},
    ]
    store.put("/r1/design/rough/layout.spec.json", json.dumps(spec0),
              source="marker", mime="application/json")
    S2aVisual(stub).run(ctx)
    spec = json.loads(store.get("/r1/design/rough/layout.spec.json").content_text)
    bg = next(s for s in spec["slots"] if s["role"] == "background")
    assert bg["asset_ref"] == "custom/hero.png"               # 기존 히어로 보존(폴백 아님)
    logo = next(s for s in spec["slots"] if s["role"] == "logo")
    assert logo["asset_ref"] == "design-system/components/logo/v1.png"   # logo 보존
    roles = {s["role"] for s in spec["slots"]}
    assert {"headline", "rate_card", "benefit_row"} <= roles  # engine 슬롯과 공존


# ── I1 회귀: rich 리뷰 교정은 S2a 재베이크를 건너뛴다(gemini 재호출 0·히어로/logo 보존) ──


def test_flag_on_remediation_skips_visual_rebake(tmp_path, monkeypatch):
    """I1: rich 모드 done-상태 카피 교정은 S2a 재베이크를 건너뛴다.
    카피는 벡터 레이어라 재생성이 불필요(유료 gemini 호출 0)하고, _run_rich의 slots 교체가
    S2c logo 슬롯을 지우는 것도 방지한다. flag off 경로(재베이크)는 test_demo_pipeline이 잠근다."""
    monkeypatch.setenv("RICH_VECTOR_CHROME", "1")
    from app.gateway.harness_design import DesignHarness
    from app.gateway.state import save_state
    from app.providers.fake import FakeProvider

    store, _ = _ctx(tmp_path)                       # plan.md + layout.spec.json 시드
    save_state(store, "r1", "design", {"step": "done", "gate": None,
               "confirmed": {}, "bypass": {}, "languages": ["ko"]})
    stub = _RichStub()
    h = DesignHarness(image_provider=stub)
    req = HarnessRequest(run_id="r1", studio="design",
                         user_prompt="리뷰 결과대로 카피 수정해줘",   # '수정' = 교정 토큰
                         provider="fake", is_marker=True)
    res = h.handle_turn(req, provider=FakeProvider(), store=store)
    assert res.meta.get("remediated") is True       # 교정 경로 진입
    assert stub.gen_prompts == []                    # S2a generate_image 재호출 0회


# ── E2E: flag-on 전체 파이프라인 완주 + S2c 호환(Task 4) ────────────────────


def test_e2e_pipeline_flag_on_produces_vector_spec_with_logo(tmp_path, monkeypatch):
    """S0→…→done 완주: render_mode + engine slots + S2c의 logo 슬롯·disclosure copy 공존.

    driving: bypass_map으로 전 gated step OFF → 한 턴 연쇄(test_demo_pipeline 패턴).
    S2a rich 분기가 slots를 layout_engine 벡터 슬롯으로 교체(headline·rate_card·
    benefit_row·cta_button·disclosure)한 뒤, S2c가 logo 슬롯(asset_ref 핀) append +
    전 언어 disclosure copy 주입. FakeProvider는 텍스트/이미지/비전 액터 3역을 모두 수행하고,
    review_image만 SEMANTIC_LAYOUT_INSTR(clear_zones 포함)에 의미 레이아웃 JSON을 응답한다.
    """
    monkeypatch.setenv("RICH_VECTOR_CHROME", "1")
    from app.gateway.harness_design import DesignHarness
    from app.providers.fake import FakeProvider

    class _RichFake(FakeProvider):
        def review_image(self, png, instr, *, mime="image/png"):
            if "clear_zones" in instr:                       # SEMANTIC_LAYOUT_INSTR
                return ProviderResponse(text=SEM_JSON, model="fake")
            return ProviderResponse(text='{"findings":[]}', model="fake")

    store = LocalVfsStore(storage_dir=str(tmp_path))
    store.create_run("r1", languages=["ko"])
    store.put("/r1/brainstorming/plan.md",
              "---\ncreative_direction:\n  aspect: \"4:5\"\n"
              "factsheet:\n  interest_rate: \"연 2.80%\"\n  max_rate: \"최고 연 3.30%\"\n"
              "  term: \"6~36개월\"\n  min_amount: \"100만원\"\n"
              "disclosures:\n  - \"예금자보호법에 따라 5천만원까지 보호\"\n"
              "material_matrix: [{channel: instagram, lang: ko}]\nlanguages: [ko]\n---\n본문",
              source="marker", mime="text/markdown")

    h = DesignHarness(image_provider=_RichFake())
    req = HarnessRequest(run_id="r1", studio="design", user_prompt="포스터",
                         provider="fake", is_marker=True, action="advance",
                         bypass_map={"S1": True, "S2b": True, "S2a": True,
                                     "S2c": True, "S3": True})
    res = h.handle_turn(req, provider=_RichFake(), store=store)

    assert res.meta.get("step") == "done"                    # 완주(게이트 정지 없음)
    spec = json.loads(store.get("/r1/design/rough/layout.spec.json").content_text)
    assert spec["render_mode"] == "vector_chrome"            # rich 벡터 크롬 spec
    roles = {s["role"] for s in spec["slots"]}
    assert {"background", "headline", "rate_card", "benefit_row", "cta_button",
            "disclosure", "logo"} <= roles                   # 히어로 background + engine 슬롯 + S2c logo 공존
    logo = next(s for s in spec["slots"] if s["role"] == "logo")
    assert logo["asset_ref"] == "design-system/components/logo/v1.png"   # S2c 핀 보존
    assert spec["copy"]["ko"]["disclosure"]                              # S2c 고지 주입
