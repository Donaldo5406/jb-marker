"""ReviewHarness — R0~R3 핸들러·게이트·ack·restart·factory 통합."""
import json
import pytest

from app.gateway.harness import HarnessRequest
from app.gateway.harness_review import (
    ReviewHarness, STEPS, PERSONA_A, PERSONA_B, PERSONA_C, PERSONA_RC,
)
from app.providers.base import ProviderResponse
from app.providers.fake import FakeProvider
from app.vfs.factory import make_local_store


def _setup_run(store, run_id="r1", languages=None):
    """공통 셋업 — run 생성 + brain plan.md + design 산출 자리."""
    languages = languages or ["ko", "en"]
    store.create_run(run_id, languages=languages)
    plan_md = (
        "---\n"
        f"languages: {languages}\n"
        "factsheet:\n  rate: 5.2\n"
        "disclosures:\n  - 미래 수익 보장 아님\n"
        "  - 세전 금리, 우대조건 충족 시\n"
        "---\n"
        "# Plan\n"
    )
    store.put(f"/{run_id}/brainstorming/plan.md", plan_md,
              source="marker", mime="text/markdown")
    # design 산출 자리
    for lang in languages:
        store.put(f"/{run_id}/design/final/{lang}/main.scene",
                  json.dumps({"copy": {lang: {"headline": "쉽고 빠르게",
                                                "cta": "지금 가입",
                                                "disclosure": "고지 텍스트"}}}),
                  source="marker", mime="application/json")
    store.put(f"/{run_id}/design/metadata.md", "콘티: 우상향 그래프\n",
              source="marker", mime="text/markdown")
    store.put(f"/{run_id}/design/design-system/components/visual/v1.png",
              b"\x89PNG\x00fake", source="gemini", mime="image/png")
    return store, run_id


def test_steps_constant():
    assert STEPS == ("R0", "R1", "R2", "RC", "R3", "done")


def test_personas_defined():
    assert "법률 검토" in PERSONA_A or "법률" in PERSONA_A
    assert "동등성" in PERSONA_B
    assert "통합" in PERSONA_C or "reconciler" in PERSONA_C.lower()
    assert "논란" in PERSONA_RC or "평판" in PERSONA_RC


def test_review_harness_initial_state(tmp_path):
    store = make_local_store(tmp_path)
    _setup_run(store)
    h = ReviewHarness(vision_provider=FakeProvider())
    # _state.json 부재 시 기본값
    state = h._load_state(store, "r1")
    assert state["step"] == "R0"
    assert state["acknowledged"] is False


def test_collect_scene_copy_reconstructs_from_objects(tmp_path):
    """실 production 경로 회귀 가드: 프론트 sceneAssembler가 저장하는 main.scene은
    top-level copy 없이 {version, objects:[{type:textbox, role, text, lang}], width, height}
    형식이다 → 백엔드가 objects에서 role→text로 카피를 복원해야 R1/R2가 콘텐츠를 본다.
    기존 백엔드 픽스처는 {copy:{lang:{...}}} 형식만 써서 이 재구성 분기를 한 번도 타지
    않았다(테스트 위장). role/type 키명·케이싱이 깨지면 scene_copy가 비어 위반 무탐이
    발생하므로 production 형식을 직접 검증한다."""
    store = make_local_store(tmp_path)
    store.create_run("r1", languages=["ko", "en"])
    for lang, head, body in [("ko", "헤드라인", "본문 카피"), ("en", "Headline", "Body copy")]:
        store.put(
            f"/r1/design/final/{lang}/main.scene",
            json.dumps({
                "version": "6.0.0", "width": 1080, "height": 1350,
                "objects": [
                    {"type": "textbox", "role": "headline", "text": head, "lang": lang},
                    {"type": "textbox", "role": "body", "text": body, "lang": lang},
                    {"type": "image", "role": "background", "src": "x"},  # image는 제외돼야
                ],
            }),
            source="marker", mime="application/json")
    h = ReviewHarness(vision_provider=FakeProvider())
    out = h._collect_scene_copy(store, "r1", ["ko", "en"])
    assert out["ko"] == {"headline": "헤드라인", "body": "본문 카피"}
    assert out["en"] == {"headline": "Headline", "body": "Body copy"}


def test_r0_setup_creates_matrix_and_sets_in_progress(tmp_path):
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko", "en"])
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="검토 시작",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)
    state = json.loads(store.get("/r1/review/_state.json").content_text)
    assert state["step"] == "R1"
    assert state["languages"] == ["ko", "en"]
    assert "ko" in state["matrix"] and "en" in state["matrix"]
    assert "visual/v1.png" in state["matrix"]["components"]
    m = store.get_manifest("r1")
    assert m.step_status.get("review") == "in_progress"


def test_r0_normalizes_object_list_languages(tmp_path):
    """FIX A: 실 Claude plan.md의 객체 리스트 languages → 문자열 코드로 정규화.

    정규화 안 하면 matrix[dict] / 경로 `.../{dict}/main.scene` 에서 unhashable·깨진 경로로
    R0가 크래시한다. 정규화 후 matrix는 문자열 키, 언어 수 정상.
    """
    store = make_local_store(tmp_path)
    store.create_run("r1", languages=["ko", "en"])
    plan_md = (
        "---\n"
        "languages:\n"
        "  - code: ko\n    label: 한국어\n    primary: true\n"
        "  - code: en\n    label: English\n"
        "factsheet:\n  rate: 5.2\n"
        "disclosures:\n  - 미래 수익 보장 아님\n"
        "---\n# Plan\n")
    store.put("/r1/brainstorming/plan.md", plan_md, source="marker", mime="text/markdown")
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="검토",
                         provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)
    state = json.loads(store.get("/r1/review/_state.json").content_text)
    assert state["languages"] == ["ko", "en"]
    assert set(state["matrix"]) >= {"ko", "en", "components"}


def test_r0_idempotent_cleanup(tmp_path):
    """R0 진입 시 legal/, i18n/, revise/, report.md 전부 삭제."""
    store = make_local_store(tmp_path)
    _setup_run(store)
    # stale 산출 미리 박아둠
    store.put("/r1/review/legal/law_stale/verdict.json", '{"x":1}',
              source="marker", mime="application/json")
    store.put("/r1/review/i18n/reason_stale/verdict.json", '{"x":1}',
              source="marker", mime="application/json")
    store.put("/r1/review/revise/text/rec_stale.md", "stale",
              source="marker", mime="text/markdown")
    store.put("/r1/review/report.md", "stale", source="marker", mime="text/markdown")
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)
    # 전부 삭제됨
    assert store.get("/r1/review/legal/law_stale/verdict.json") is None
    assert store.get("/r1/review/i18n/reason_stale/verdict.json") is None
    assert store.get("/r1/review/revise/text/rec_stale.md") is None
    assert store.get("/r1/review/report.md") is None


def test_r0_render_matrix_detects_uploaded(tmp_path):
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko", "en"])
    store.put("/r1/review/_render/ko.png", b"\x89PNG", source="frontend", mime="image/png")
    # en은 미업로드
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)
    state = json.loads(store.get("/r1/review/_state.json").content_text)
    assert state["matrix"]["ko"]["render"] is True
    assert state["matrix"]["en"]["render"] is False


def test_r1_legal_text_search_persists_verdicts(tmp_path, make_scripted):
    from app.providers.base import ProviderResponse
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko"])
    # R0 먼저 실행
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)
    # 텍스트 provider: 1 finding (화이트리스트 통과)
    text_provider = make_scripted(complete_responses=[ProviderResponse(
        text=('{"findings":[{"location":{"slot":"headline","lang":"ko"},'
              '"clause":"표시광고법 §3 ①",'
              '"official_source_url":"https://law.go.kr/x",'
              '"severity":"critical","evidence":"\\uD655\\uC2E4\\uD788 \\uC218\\uC775"}]}'),
        model="x")])
    h.handle_turn(req, provider=text_provider, store=store)
    # legal/ 아래 verdict 1건
    nodes = store.list("/r1/review/legal/")
    verdict_files = [n for n in nodes if n.path.endswith("verdict.json")]
    assert len(verdict_files) == 1
    v = json.loads(verdict_files[0].content_text)
    assert v["node"] == "legal"
    assert v["severity"] == "critical"
    assert v["location"]["slot"] == "headline"
    assert v["verdict_id"].startswith("legal")  # 안정 ID prefix
    # state 전이
    state = json.loads(store.get("/r1/review/_state.json").content_text)
    assert state["step"] == "R2"


def test_r1_visual_violation_persists_legal_verdict(tmp_path):
    """#3: R1의 결정론 시각 검사(core/visual_rules)가 layout.spec의 시각 위반을
    legal verdict(kind=visual)로 영속 → 게이트에 합류. (텍스트 finding 없이도 검출.)"""
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko"])
    # 고지 글자크기 위반(10px = 최대 72px의 14% < 30%). 고지 슬롯·카피는 존재(R-VIS-3 통과).
    store.put("/r1/design/rough/layout.spec.json", json.dumps({
        "bg_color": "#FFFFFF",
        "slots": [
            {"role": "headline", "font_px": 72, "color": "#000000"},
            {"role": "disclosure", "font_px": 10, "color": "#000000"},
        ],
        "copy": {"ko": {"disclosure": "예금자보호법에 따라 5천만원까지 보호"}},
    }), source="marker", mime="application/json")
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)   # R0
    h.handle_turn(req, provider=FakeProvider(), store=store)   # R1(텍스트 0건 + 결정론 시각 검사)
    verdicts = h._load_all_verdicts(store, "r1")
    visual = [v for v in verdicts if v.get("kind") == "visual"]
    assert visual, f"시각 verdict 미검출: {verdicts}"
    assert any(v["severity"] == "warning" for v in visual)
    assert all(v["node"] == "legal" for v in visual)          # legal 노드로 합류


def test_r1_legal_whitelist_drops_off_source(tmp_path, make_scripted):
    from app.providers.base import ProviderResponse
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko"])
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R0
    text_provider = make_scripted(complete_responses=[ProviderResponse(
        text=('{"findings":[{"location":{"slot":"headline","lang":"ko"},'
              '"clause":"§X","official_source_url":"https://blog.com/x",'
              '"severity":"critical","evidence":"x"}]}'),
        model="x")])
    h.handle_turn(req, provider=text_provider, store=store)
    nodes = store.list("/r1/review/legal/")
    assert [n for n in nodes if n.path.endswith("verdict.json")] == []
    state = json.loads(store.get("/r1/review/_state.json").content_text)
    assert state["dropped_findings_count"] >= 1


def test_r1_component_vision_persists_visual_verdict(tmp_path, make_scripted):
    from app.providers.base import ProviderResponse
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko"])
    h = ReviewHarness(vision_provider=make_scripted(
        review_image_responses=[ProviderResponse(
            text=('{"findings":[{"location":{"slot":"visual","lang":null},'
                  '"clause":"표시광고법 §3 ①",'
                  '"official_source_url":"https://law.go.kr/v",'
                  '"severity":"critical",'
                  '"evidence":"이미지에 \\"확실한 수익\\" 텍스트 박힘"}]}'),
            model="g")]))
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R0
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R1 (text 빈, component vision 1건)
    nodes = store.list("/r1/review/legal/")
    visual_verdicts = []
    for n in nodes:
        if n.path.endswith("verdict.json"):
            v = json.loads(n.content_text)
            if v["location"]["slot"] == "visual":
                visual_verdicts.append(v)
    assert len(visual_verdicts) == 1
    assert visual_verdicts[0]["lang"] is None
    assert visual_verdicts[0]["severity"] == "critical"


def test_r1_component_vision_skipped_when_v1_missing(tmp_path):
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko"])
    store.delete("/r1/design/design-system/components/visual/v1.png")
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R0
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R1
    state = json.loads(store.get("/r1/review/_state.json").content_text)
    assert "visual/v1.png" in state["vision_skipped"]


def test_r1_composite_vision_per_lang_persists(tmp_path, make_scripted):
    from app.providers.base import ProviderResponse
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko", "en"])
    # 두 언어 모두 render 업로드
    store.put("/r1/review/_render/ko.png", b"\x89PNG-ko", source="frontend", mime="image/png")
    store.put("/r1/review/_render/en.png", b"\x89PNG-en", source="frontend", mime="image/png")
    h = ReviewHarness(vision_provider=make_scripted(review_image_responses=[
        # ko 컴포넌트 비전(v1.png 호출): 빈
        ProviderResponse(text='{"findings":[]}', model="g"),
        # ko composite
        ProviderResponse(text=('{"findings":[{"location":{"slot":"composite","lang":"ko"},'
                                '"clause":"금융광고규정","official_source_url":"https://fss.or.kr/x",'
                                '"severity":"warning","evidence":"고지 가독성 저하"}]}'), model="g"),
        # en composite
        ProviderResponse(text=('{"findings":[{"location":{"slot":"composite","lang":"en"},'
                                '"clause":"§Y","official_source_url":"https://law.go.kr/y",'
                                '"severity":"warning","evidence":"x"}]}'), model="g"),
    ]))
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R0
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R1
    composite = []
    for n in store.list("/r1/review/legal/"):
        if n.path.endswith("verdict.json"):
            v = json.loads(n.content_text)
            if v["location"]["slot"] == "composite":
                composite.append(v)
    assert len(composite) == 2
    langs = {v["lang"] for v in composite}
    assert langs == {"ko", "en"}


def test_r1_composite_vision_skipped_per_lang(tmp_path, make_scripted):
    from app.providers.base import ProviderResponse
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko", "en"])
    store.put("/r1/review/_render/ko.png", b"\x89PNG", source="frontend", mime="image/png")
    # en render 부재
    h = ReviewHarness(vision_provider=make_scripted(review_image_responses=[
        ProviderResponse(text='{"findings":[]}', model="g"),  # v1.png
        ProviderResponse(text='{"findings":[]}', model="g"),  # ko composite
        # en composite은 부재라 호출 안 됨
    ]))
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R0
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R1
    state = json.loads(store.get("/r1/review/_state.json").content_text)
    assert "composite/en" in state["vision_skipped"]
    assert "composite/ko" not in state["vision_skipped"]


def test_r1_graceful_no_live_search(tmp_path, make_scripted):
    """provider.complete 자체 크래시 → live_unavailable=true, step 500 없음."""
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko"])
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R0
    failing = make_scripted(complete_raises=RuntimeError("no key"))
    h.handle_turn(req, provider=failing, store=store)  # R1 — 크래시 없이 통과
    state = json.loads(store.get("/r1/review/_state.json").content_text)
    assert state["live_unavailable"] is True
    assert state["step"] == "R2"


def test_r1_graceful_parse_failed(tmp_path, make_scripted):
    from app.providers.base import ProviderResponse
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko"])
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R0
    bad = make_scripted(complete_responses=[ProviderResponse(text="not json", model="x")])
    h.handle_turn(req, provider=bad, store=store)  # R1
    state = json.loads(store.get("/r1/review/_state.json").content_text)
    assert state["parse_failed"] is True


def test_r1_graceful_vision_failed(tmp_path, make_scripted):
    """vision_provider.review_image 크래시 → vision_failed=true."""
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko"])
    h = ReviewHarness(vision_provider=make_scripted(
        review_image_raises=RuntimeError("vision down")))
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R0
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R1
    state = json.loads(store.get("/r1/review/_state.json").content_text)
    assert state["vision_failed"] is True


def test_r2_i18n_persists_findings(tmp_path, make_scripted):
    from app.providers.base import ProviderResponse
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko", "en"])
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R0
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R1 (FakeProvider → 빈)
    text_provider = make_scripted(complete_responses=[ProviderResponse(
        text=('{"findings":[{"lang":"en","kind":"missing_disclosure",'
              '"severity":"critical","evidence":"...",'
              '"disclosure":"미래 수익 보장 아님"}]}'), model="x")])
    h.handle_turn(req, provider=text_provider, store=store)  # R2
    nodes = store.list("/r1/review/i18n/")
    verdicts = [json.loads(n.content_text) for n in nodes
                if n.path.endswith("verdict.json")]
    assert len(verdicts) == 1
    assert verdicts[0]["node"] == "i18n"
    assert verdicts[0]["kind"] == "missing_disclosure"
    assert verdicts[0]["severity"] == "critical"
    state = json.loads(store.get("/r1/review/_state.json").content_text)
    assert state["step"] == "RC"


def test_r2_keyword_safety_net_adds_missing(tmp_path, make_scripted):
    """LLM이 missing_disclosure를 누락해도 키워드 매핑 안전망이 잡음."""
    from app.providers.base import ProviderResponse
    store = make_local_store(tmp_path)
    # en 자산이 필수고지 키워드를 포함하지 않게 셋업
    store.create_run("r1", languages=["ko", "en"])
    plan_md = (
        "---\n"
        "languages: [ko, en]\n"
        "disclosures:\n  - 미래 수익 보장 아님\n"
        "---\n"
    )
    store.put("/r1/brainstorming/plan.md", plan_md, source="marker", mime="text/markdown")
    store.put("/r1/design/final/ko/main.scene", json.dumps({"copy": {"ko": {
        "headline": "쉽고 빠르게", "disclosure": "미래 수익 보장 아님"}}}),
        source="marker", mime="application/json")
    store.put("/r1/design/final/en/main.scene", json.dumps({"copy": {"en": {
        "headline": "Fast and easy", "disclosure": "Terms apply"}}}),
        source="marker", mime="application/json")
    store.put("/r1/design/metadata.md", "", source="marker", mime="text/markdown")
    store.put("/r1/design/design-system/components/visual/v1.png",
              b"\x89PNG", source="gemini", mime="image/png")

    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R0
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R1
    # LLM은 findings=[] 반환(누락)
    text_provider = make_scripted(complete_responses=[ProviderResponse(
        text='{"findings":[]}', model="x")])
    h.handle_turn(req, provider=text_provider, store=store)  # R2
    # 안전망이 missing_disclosure를 추가했어야
    nodes = store.list("/r1/review/i18n/")
    verdicts = [json.loads(n.content_text) for n in nodes if n.path.endswith("verdict.json")]
    safety_net = [v for v in verdicts if v.get("kind") == "missing_disclosure"]
    assert len(safety_net) >= 1
    assert safety_net[0]["severity"] == "critical"


def test_r2_skipped_mono_lingual(tmp_path):
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko"])
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R0
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R1
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R2 → 스킵
    state = json.loads(store.get("/r1/review/_state.json").content_text)
    assert state["r2_skipped"] == "mono-lingual"
    assert state["step"] == "RC"
    # i18n/ 비어 있음
    nodes = store.list("/r1/review/i18n/")
    assert [n for n in nodes if n.path.endswith("verdict.json")] == []


def test_r3_persists_recommendations_and_report(tmp_path, make_scripted):
    store = make_local_store(tmp_path)
    # R1/R2가 이미 끝난 상태로 verdict 미리 박아둠
    store.create_run("r1", languages=["ko", "en"])
    store.put("/r1/brainstorming/plan.md",
              "---\nlanguages: [ko, en]\ndisclosures: []\n---\n",
              source="marker", mime="text/markdown")
    store.put("/r1/review/legal/law_abc/verdict.json",
              json.dumps({"verdict_id": "legal_abc", "node": "legal",
                          "severity": "warning",
                          "location": {"slot": "headline", "lang": "ko"},
                          "lang": "ko",
                          "clause": "§X", "evidence": "x"}),
              source="marker", mime="application/json")
    store.put("/r1/review/i18n/reason_def/verdict.json",
              json.dumps({"verdict_id": "i18n_def", "node": "i18n",
                          "severity": "warning",
                          "location": {"slot": "disclosure", "lang": "en"},
                          "lang": "en",
                          "kind": "mistranslation", "evidence": "x"}),
              source="marker", mime="application/json")
    # state=R3
    state = {
        "step": "R3", "languages": ["ko", "en"], "matrix": {},
        "acknowledged": False, "live_unavailable": False, "parse_failed": False,
        "vision_failed": False, "step_failed": "",
        "vision_skipped": [], "dropped_findings_count": 0, "r2_skipped": "",
    }
    store.put("/r1/review/_state.json", json.dumps(state),
              source="marker", mime="application/json")

    text_provider = make_scripted(complete_responses=[ProviderResponse(
        text=('{"recommendations":[{"asset_id":"design/final/ko/main.scene",'
              '"lang":"ko","target":"text","instruction":"헤드라인 교체",'
              '"priority":1,"related_verdict_ids":["legal_abc"]}],'
              '"conflicts_resolved":[]}'),
        model="x")])
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=text_provider, store=store)
    # revise/text/rec_*.md 존재
    rec_nodes = [n for n in store.list("/r1/review/revise/text/")
                  if n.path.endswith(".md")]
    assert len(rec_nodes) == 1
    # report.md 존재 + frontmatter 포함
    report = store.get("/r1/review/report.md")
    assert report is not None
    assert "gate:" in report.content_text
    state = json.loads(store.get("/r1/review/_state.json").content_text)
    assert state["step"] == "done"


# ===== T1-P3 Task 5: PromptSpec 전환 — system 보존(D6) + meta 명시 신호 =====


def test_r2_system_is_persona_b_and_meta_passed(tmp_path, make_scripted):
    """T1-P3 D6: R2는 PERSONA_B를 그대로 system으로 전달(조립 없음) +
    meta={"studio":"review","step":"R2"} 명시 신호 + model= 미전달."""
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko", "en"])
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R0
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R1
    sp = make_scripted(complete_responses=[ProviderResponse(
        text='{"findings":[]}', model="x")])
    h.handle_turn(req, provider=sp, store=store)  # R2
    call = sp.calls_complete[0]
    assert call["system"] == PERSONA_B
    assert call["kw"].get("meta") == {"studio": "review", "step": "R2", "medium": "image"}
    assert call["model"] is None  # model=provider.name 제거


def test_r3_system_is_persona_c_and_meta_passed(tmp_path, make_scripted):
    """T1-P3 D6: R3는 PERSONA_C를 그대로 system으로 전달 +
    meta={"studio":"review","step":"R3"} 명시 신호 + model= 미전달."""
    store = make_local_store(tmp_path)
    store.create_run("r1", languages=["ko"])
    store.put("/r1/brainstorming/plan.md", "---\nlanguages: [ko]\n---\n",
              source="marker", mime="text/markdown")
    state = {"step": "R3", "languages": ["ko"], "matrix": {},
             "acknowledged": False, "live_unavailable": False,
             "parse_failed": False, "vision_failed": False,
             "step_failed": "", "vision_skipped": [],
             "dropped_findings_count": 0, "r2_skipped": ""}
    store.put("/r1/review/_state.json", json.dumps(state),
              source="marker", mime="application/json")
    sp = make_scripted(complete_responses=[ProviderResponse(
        text='{"recommendations":[],"conflicts_resolved":[]}', model="x")])
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=sp, store=store)  # R3
    call = sp.calls_complete[0]
    assert call["system"] == PERSONA_C
    assert call["kw"].get("meta") == {"studio": "review", "step": "R3", "medium": "image"}
    assert call["model"] is None


# ===== Task 14: 게이트 산정 → manifest.step_status =====


@pytest.mark.parametrize("verdicts_and_expected", [
    ([], "PASS"),
    ([{"severity": "warning"}], "WARN"),
    ([{"severity": "critical"}], "BLOCKED"),
    ([{"severity": "critical"}, {"severity": "warning"}], "BLOCKED"),
])
def test_r3_gate_status_set_on_manifest(tmp_path, make_scripted, verdicts_and_expected):
    from app.providers.base import ProviderResponse
    verdicts, expected = verdicts_and_expected
    store = make_local_store(tmp_path)
    store.create_run("r1", languages=["ko"])
    store.put("/r1/brainstorming/plan.md", "---\nlanguages: [ko]\n---\n",
              source="marker", mime="text/markdown")
    for i, v in enumerate(verdicts):
        store.put(f"/r1/review/legal/law_{i}/verdict.json",
                  json.dumps({**v, "verdict_id": f"legal_{i}",
                              "location": {"slot": "headline", "lang": "ko"}}),
                  source="marker", mime="application/json")
    state = {"step": "R3", "languages": ["ko"], "matrix": {},
             "acknowledged": False, "live_unavailable": False,
             "parse_failed": False, "vision_failed": False,
             "step_failed": "", "vision_skipped": [],
             "dropped_findings_count": 0, "r2_skipped": ""}
    store.put("/r1/review/_state.json", json.dumps(state),
              source="marker", mime="application/json")
    text_provider = make_scripted(complete_responses=[ProviderResponse(
        text='{"recommendations":[],"conflicts_resolved":[]}', model="x")])
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=text_provider, store=store)
    m = store.get_manifest("r1")
    assert m.step_status.get("review") == expected


@pytest.mark.parametrize("flag_key,flag_val", [
    ("live_unavailable", True),
    ("parse_failed", True),
    ("vision_failed", True),
    ("step_failed", "R1"),
    ("vision_skipped", ["visual/v1.png"]),
])
def test_r3_pass_demoted_to_warn_per_trigger(tmp_path, make_scripted, flag_key, flag_val):
    """verdict 0건이어도 5트리거 중 하나라도 켜져 있으면 PASS→WARN 강등."""
    from app.providers.base import ProviderResponse
    store = make_local_store(tmp_path)
    store.create_run("r1", languages=["ko"])
    store.put("/r1/brainstorming/plan.md", "---\nlanguages: [ko]\n---\n",
              source="marker", mime="text/markdown")
    state = {"step": "R3", "languages": ["ko"], "matrix": {},
             "acknowledged": False, "live_unavailable": False,
             "parse_failed": False, "vision_failed": False,
             "step_failed": "", "vision_skipped": [],
             "dropped_findings_count": 0, "r2_skipped": "",
             flag_key: flag_val}
    store.put("/r1/review/_state.json", json.dumps(state),
              source="marker", mime="application/json")
    text_provider = make_scripted(complete_responses=[ProviderResponse(
        text='{"recommendations":[],"conflicts_resolved":[]}', model="x")])
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=text_provider, store=store)
    m = store.get_manifest("r1")
    assert m.step_status.get("review") == "WARN"


# ===== Task 15: ack / restart / regenerate =====


def test_action_ack_sets_acknowledged_only_on_warn(tmp_path, make_scripted):
    from app.providers.base import ProviderResponse
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko"])
    text_provider = make_scripted(complete_responses=[
        ProviderResponse(text='{"findings":[{"location":{"slot":"headline","lang":"ko"},'
                               '"clause":"§X","official_source_url":"https://law.go.kr/x",'
                               '"severity":"warning","evidence":"x"}]}', model="x"),  # R1
        ProviderResponse(text='{"findings":[]}', model="x"),  # RC (LLM 경로)
        ProviderResponse(text='{"recommendations":[],"conflicts_resolved":[]}', model="x"),  # R3
    ])
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R0
    h.handle_turn(req, provider=text_provider, store=store)  # R1 (warning 1건)
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R2 (mono-lingual skip) → RC
    h.handle_turn(req, provider=text_provider, store=store)  # RC → R3
    h.handle_turn(req, provider=text_provider, store=store)  # R3 reconcile → WARN
    m = store.get_manifest("r1")
    assert m.step_status.get("review") == "WARN"

    # ack 호출
    ack_req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                              provider="fake", is_marker=True, action="ack")
    h.handle_turn(ack_req, provider=FakeProvider(), store=store)
    state = json.loads(store.get("/r1/review/_state.json").content_text)
    assert state["acknowledged"] is True
    # step_status는 WARN 유지(신호 보존)
    m2 = store.get_manifest("r1")
    assert m2.step_status.get("review") == "WARN"


def test_action_restart_resets_to_r0(tmp_path, make_scripted):
    from app.providers.base import ProviderResponse
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko"])
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R0
    # stale 영속
    store.put("/r1/review/legal/law_x/verdict.json", '{"x":1}',
              source="marker", mime="application/json")
    # restart
    restart_req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                                  provider="fake", is_marker=True, action="restart")
    h.handle_turn(restart_req, provider=FakeProvider(), store=store)
    # stale 삭제 + step=R1(R0 재실행 후 자동 전이)
    assert store.get("/r1/review/legal/law_x/verdict.json") is None
    state = json.loads(store.get("/r1/review/_state.json").content_text)
    assert state["step"] == "R1"
    assert state["acknowledged"] is False


def test_action_restart_idempotent_same_id(tmp_path, make_scripted):
    """동일 finding 재검출 시 같은 verdict_id로 영속(멱등)."""
    from app.providers.base import ProviderResponse
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko"])
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R0
    text_provider1 = make_scripted(complete_responses=[ProviderResponse(
        text=('{"findings":[{"location":{"slot":"headline","lang":"ko"},'
              '"clause":"§A","official_source_url":"https://law.go.kr/a",'
              '"severity":"warning","evidence":"x"}]}'), model="x")])
    h.handle_turn(req, provider=text_provider1, store=store)  # R1
    nodes1 = [n.path for n in store.list("/r1/review/legal/") if n.path.endswith("verdict.json")]
    # restart + 동일 finding 재검출
    restart = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                              provider="fake", is_marker=True, action="restart")
    h.handle_turn(restart, provider=FakeProvider(), store=store)
    text_provider2 = make_scripted(complete_responses=[ProviderResponse(
        text=('{"findings":[{"location":{"slot":"headline","lang":"ko"},'
              '"clause":"§A","official_source_url":"https://law.go.kr/a",'
              '"severity":"warning","evidence":"x"}]}'), model="x")])
    h.handle_turn(req, provider=text_provider2, store=store)
    nodes2 = [n.path for n in store.list("/r1/review/legal/") if n.path.endswith("verdict.json")]
    assert nodes1 == nodes2  # 같은 경로(=같은 verdict_id)


# ===== Task 16: server.py 하네스 팩토리 — review+marker → ReviewHarness =====


def test_server_factory_review_marker_selects_review_harness(tmp_path, monkeypatch):
    """server.py 하네스 팩토리에서 review+marker → ReviewHarness.

    R0가 실행되면 step_status['review']='in_progress'로 셋되며
    이는 ReviewHarness가 호출된 직접 증거다. PassthroughHarness는 이를 세팅하지 않는다.
    """
    from fastapi.testclient import TestClient
    from app.server import create_app

    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("JBM_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "true")
    client = TestClient(create_app())

    # run 생성
    r = client.post("/runs", json={"languages": ["ko"]})
    assert r.status_code == 200
    run_id = r.json()["run_id"]

    # design 산출 박아두기 (server.py의 PUT /vfs/{run_id}/{rest:path} 사용)
    client.put(f"/vfs/{run_id}/brainstorming/plan.md", json={
        "content": "---\nlanguages: [ko]\ndisclosures: []\n---\n",
        "mime": "text/markdown",
    })
    client.put(f"/vfs/{run_id}/design/final/ko/main.scene", json={
        "content": '{"copy":{"ko":{"headline":"x"}}}',
        "mime": "application/json",
    })
    client.put(f"/vfs/{run_id}/design/metadata.md", json={
        "content": "", "mime": "text/markdown",
    })

    # review+marker gateway 호출 (FakeProvider)
    g = client.post("/gateway/run", json={
        "run_id": run_id, "studio": "review", "is_marker": True,
        "provider": "fake", "prompt": "검토 시작",
    })
    assert g.status_code == 200

    # 응답 정상 + manifest에 review step_status 기록 (PassthroughHarness였다면 미세팅)
    runs = client.get("/runs").json()["runs"]
    run = next(x for x in runs if x["run_id"] == run_id)
    assert run["step_status"].get("review") == "in_progress"


# ===== Task 22: 통합 골든 패스 — BLOCKED/WARN/PASS 3 시나리오 =====


def _full_pipeline(store, h, req, text_responses, vision_responses=None):
    """공통 헬퍼 — R0 → R1 → R2 → R3 한 번에 흘림.

    R0는 FakeProvider로 1턴 진행해 matrix·state를 초기화.
    이후 단계는 ScriptedProvider(text)와 주입된 vision_provider(scripted)를 사용.
    """
    from conftest import ScriptedProvider
    # R0: FakeProvider만 사용 (matrix·state 초기화)
    h.handle_turn(req, provider=FakeProvider(), store=store)
    # 이후 단계: scripted text/vision providers
    text_sp = ScriptedProvider(complete_responses=list(text_responses))
    vis_sp = ScriptedProvider(review_image_responses=list(vision_responses or []))
    h._vision_provider = vis_sp
    while True:
        state = json.loads(store.get(f"/{req.run_id}/review/_state.json").content_text)
        if state["step"] == "done":
            break
        h.handle_turn(req, provider=text_sp, store=store)


def test_golden_path_blocked(tmp_path, make_scripted):
    """critical finding 1건 → BLOCKED."""
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko", "en"])
    store.put("/r1/review/_render/ko.png", b"\x89PNG-ko",
              source="frontend", mime="image/png")
    store.put("/r1/review/_render/en.png", b"\x89PNG-en",
              source="frontend", mime="image/png")
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    _full_pipeline(store, h, req,
        text_responses=[
            ProviderResponse(text=(  # R1 text: critical finding 1건
                '{"findings":[{"location":{"slot":"headline","lang":"ko"},'
                '"clause":"§3","official_source_url":"https://law.go.kr/x",'
                '"severity":"critical","evidence":"x"}]}'), model="x"),
            ProviderResponse(text='{"findings":[]}', model="x"),  # R2 i18n
            ProviderResponse(text='{"findings":[]}', model="x"),  # RC 논란
            ProviderResponse(text='{"recommendations":[],"conflicts_resolved":[]}',
                              model="x"),  # R3 reconciler
        ],
        vision_responses=[
            ProviderResponse(text='{"findings":[]}', model="g"),  # R1 v1.png
            ProviderResponse(text='{"findings":[]}', model="g"),  # R1 ko composite
            ProviderResponse(text='{"findings":[]}', model="g"),  # R1 en composite
            ProviderResponse(text='{"findings":[]}', model="g"),  # RC v1.png
        ])
    m = store.get_manifest("r1")
    assert m.step_status["review"] == "BLOCKED"


def test_golden_path_warn(tmp_path, make_scripted):
    """warning finding 1건 + 트리거 0 → WARN."""
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko", "en"])
    # plan.md.disclosures를 비워 R2 키워드 안전망이 critical을 만들지 않게 한다.
    # (안전망이 발화하면 critical>0이 되어 BLOCKED으로 강등됨)
    store.put("/r1/brainstorming/plan.md",
              "---\nlanguages: [ko, en]\ndisclosures: []\n---\n",
              source="marker", mime="text/markdown")
    store.put("/r1/review/_render/ko.png", b"\x89PNG-ko",
              source="frontend", mime="image/png")
    store.put("/r1/review/_render/en.png", b"\x89PNG-en",
              source="frontend", mime="image/png")
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    _full_pipeline(store, h, req,
        text_responses=[
            ProviderResponse(text=(  # R1 text: warning 1건
                '{"findings":[{"location":{"slot":"headline","lang":"ko"},'
                '"clause":"§X","official_source_url":"https://law.go.kr/x",'
                '"severity":"warning","evidence":"x"}]}'), model="x"),
            ProviderResponse(text='{"findings":[]}', model="x"),  # R2 i18n
            ProviderResponse(text='{"findings":[]}', model="x"),  # RC 논란
            ProviderResponse(text='{"recommendations":[],"conflicts_resolved":[]}',
                              model="x"),  # R3 reconciler
        ],
        vision_responses=[
            ProviderResponse(text='{"findings":[]}', model="g"),  # R1 v1.png
            ProviderResponse(text='{"findings":[]}', model="g"),  # R1 ko composite
            ProviderResponse(text='{"findings":[]}', model="g"),  # R1 en composite
            ProviderResponse(text='{"findings":[]}', model="g"),  # RC v1.png
        ])
    m = store.get_manifest("r1")
    assert m.step_status["review"] == "WARN"


def test_golden_path_pass(tmp_path, make_scripted):
    """위반 0건 + 모든 렌더 존재 + 라이브 OK → PASS."""
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko", "en"])
    store.put("/r1/review/_render/ko.png", b"\x89PNG-ko",
              source="frontend", mime="image/png")
    store.put("/r1/review/_render/en.png", b"\x89PNG-en",
              source="frontend", mime="image/png")
    # plan.md.disclosures 비워서 안전망이 발화하지 않게
    store.put("/r1/brainstorming/plan.md",
              "---\nlanguages: [ko, en]\ndisclosures: []\n---\n",
              source="marker", mime="text/markdown")
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    _full_pipeline(store, h, req,
        text_responses=[
            ProviderResponse(text='{"findings":[]}', model="x"),  # R1 text
            ProviderResponse(text='{"findings":[]}', model="x"),  # R2 i18n
            ProviderResponse(text='{"findings":[]}', model="x"),  # RC 논란
            ProviderResponse(text='{"recommendations":[],"conflicts_resolved":[]}',
                              model="x"),  # R3 reconciler
        ],
        vision_responses=[
            ProviderResponse(text='{"findings":[]}', model="g"),  # R1 v1.png
            ProviderResponse(text='{"findings":[]}', model="g"),  # R1 ko composite
            ProviderResponse(text='{"findings":[]}', model="g"),  # R1 en composite
            ProviderResponse(text='{"findings":[]}', model="g"),  # RC v1.png
        ])
    m = store.get_manifest("r1")
    assert m.step_status["review"] == "PASS"


# ===== RC 논란 검토 노드 =====


def test_rc_transition_r2_to_rc_to_r3(tmp_path):
    """R2 → RC → R3 전이(mono-lingual도 RC는 실행)."""
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko"])
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R0
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R1
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R2 (mono skip) → RC
    state = json.loads(store.get("/r1/review/_state.json").content_text)
    assert state["step"] == "RC"
    h.handle_turn(req, provider=FakeProvider(), store=store)  # RC → R3
    state = json.loads(store.get("/r1/review/_state.json").content_text)
    assert state["step"] == "R3"


def test_rc_deterministic_persists_controversy_verdict(tmp_path):
    """블랙리스트 신호가 있는 카피 → node=controversy verdict를 결정론으로 영속(provider 무관)."""
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko"])
    # ko main.scene 카피에 Tier-1 신호(욱일기) 주입
    store.put("/r1/design/final/ko/main.scene",
              json.dumps({"copy": {"ko": {"headline": "욱일기 느낌 배경", "cta": "가입"}}}),
              source="marker", mime="application/json")
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    for _ in range(4):  # R0,R1,R2,RC
        h.handle_turn(req, provider=FakeProvider(), store=store)
    verdicts = h._load_all_verdicts(store, "r1")
    cx = [v for v in verdicts if v.get("node") == "controversy"]
    assert cx, f"controversy verdict 미검출: {verdicts}"
    assert cx[0]["severity"] == "critical"
    # controversy/ 폴더에 risk_ 프리픽스로 영속
    paths = [n.path for n in store.list("/r1/review/controversy/")]
    assert any("/controversy/risk_" in p for p in paths)


def test_rc_controversy_joins_gate_blocked(tmp_path, make_scripted):
    """controversy critical → R3 게이트 BLOCKED."""
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko"])
    store.put("/r1/design/final/ko/main.scene",
              json.dumps({"copy": {"ko": {"headline": "1488 캠페인"}}}),
              source="marker", mime="application/json")
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    for _ in range(4):  # R0,R1,R2,RC
        h.handle_turn(req, provider=FakeProvider(), store=store)
    # R3 reconcile
    text_provider = make_scripted(complete_responses=[ProviderResponse(
        text='{"recommendations":[],"conflicts_resolved":[]}', model="x")])
    h.handle_turn(req, provider=text_provider, store=store)  # RC done → R3
    m = store.get_manifest("r1")
    assert m.step_status.get("review") == "BLOCKED"


def test_rc_clean_copy_no_findings(tmp_path):
    """clean 카피 → controversy verdict 0(중립성·오탐 가드)."""
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko"])  # 기본 카피 '쉽고 빠르게'는 clean
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    for _ in range(4):
        h.handle_turn(req, provider=FakeProvider(), store=store)
    cx = [v for v in h._load_all_verdicts(store, "r1") if v.get("node") == "controversy"]
    assert cx == []


def test_rc_system_is_persona_rc_and_meta_passed(tmp_path, make_scripted):
    """RC LLM 경로: system=PERSONA_RC, meta={"studio":"review","step":"RC"}."""
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko"])
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R0
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R1
    h.handle_turn(req, provider=FakeProvider(), store=store)  # R2 → RC
    sp = make_scripted(complete_responses=[ProviderResponse(
        text='{"findings":[]}', model="x")])
    h.handle_turn(req, provider=sp, store=store)  # RC
    call = sp.calls_complete[0]
    assert call["system"] == PERSONA_RC
    assert call["kw"].get("meta") == {"studio": "review", "step": "RC", "medium": "image"}


def test_rc_demo_provider_deterministic_catch(tmp_path):
    """DemoProvider RC 라우트: 논란 신호 카피 → 콘텐츠 기반 결정론 finding(라이브 키 불요)."""
    from app.providers.demo import DemoProvider
    from app.providers.base import Message
    p = DemoProvider()
    payload = json.dumps({"scene_copy": {"ko": {"headline": "욱일기 배경"}},
                          "blacklist_categories": []}, ensure_ascii=False)
    resp = p.complete([Message("user", payload)], meta={"studio": "review", "step": "RC"})
    data = json.loads(resp.text)
    assert data["findings"] and data["findings"][0]["severity"] == "critical"


def test_rc_verdict_id_collision_preserves_critical(tmp_path):
    """회귀 가드(verdict_id 충돌): 같은 (category, lang)의 서로 다른 두 controversy finding이
    동일 verdict 경로로 충돌해 나중 것이 앞 것을 덮어써 Tier-1 critical이 강등되던 결함.

    '욱일기 배경의 전라도 홍어 축제'는 symbol_rising_sun(critical, other_sensitive)과
    ctx_region_hongeo(warning, other_sensitive)를 동시 트리거한다 — 둘 다 category=
    other_sensitive·lang=ko라, id 기반 식별이 없으면 한 경로로 충돌해 warning(나중 것)만
    남고 critical이 사라진다. id 식별 후엔 두 verdict가 모두 보존되고 critical이 살아남아야
    한다. (FakeProvider text+vision이라 경로2(LLM)·경로3(비전)은 무탐 → 경로1만 검증.)"""
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko"])
    store.put("/r1/design/final/ko/main.scene",
              json.dumps({"copy": {"ko": {"headline": "욱일기 배경의 전라도 홍어 축제"}}}),
              source="marker", mime="application/json")
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="fake", is_marker=True)
    for _ in range(4):  # R0, R1, R2(mono skip), RC
        h.handle_turn(req, provider=FakeProvider(), store=store)
    cx = [v for v in h._load_all_verdicts(store, "r1") if v.get("node") == "controversy"]
    assert len(cx) == 2, f"두 controversy verdict가 모두 보존돼야 함(충돌 방지): {cx}"
    assert any(v["severity"] == "critical" for v in cx), \
        f"rising-sun critical이 보존돼야 함(강등 방지): {cx}"


def test_rc_demo_path2_shares_id_with_path1_idempotent(tmp_path):
    """회귀 가드(멱등): DemoProvider(mock LLM) RC 경로2 finding이 id를 실어 경로1(결정론)과
    동일 verdict_id로 수렴 → 같은 finding이 두 경로에서 중복 파일이 되지 않는다.

    2신호 카피는 경로1·경로2 각각 2건이나 id가 겹쳐 총 2개 verdict 파일만 남아야 한다(demo.py가
    id를 안 실으면 경로2가 category로 뭉쳐 별도 파일을 만들어 3개가 됨)."""
    from app.providers.demo import DemoProvider
    store = make_local_store(tmp_path)
    _setup_run(store, languages=["ko"])
    store.put("/r1/design/final/ko/main.scene",
              json.dumps({"copy": {"ko": {"headline": "욱일기 배경의 전라도 홍어 축제"}}}),
              source="marker", mime="application/json")
    h = ReviewHarness(vision_provider=FakeProvider())
    req = HarnessRequest(run_id="r1", studio="review", user_prompt="",
                          provider="demo", is_marker=True)
    for _ in range(4):  # R0, R1, R2(mono skip), RC
        h.handle_turn(req, provider=DemoProvider(), store=store)
    files = [n.path for n in store.list("/r1/review/controversy/")
             if n.path.endswith("verdict.json")]
    assert len(files) == 2, f"경로1·경로2가 id로 수렴해 2개만 남아야 함(중복 방지): {files}"
    cx = [v for v in h._load_all_verdicts(store, "r1") if v.get("node") == "controversy"]
    assert any(v["severity"] == "critical" for v in cx)
