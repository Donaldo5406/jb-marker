"""ReviewHarness — R0~R3 핸들러·게이트·ack·restart·factory 통합."""
import json
import pytest

from app.gateway.harness import HarnessRequest
from app.gateway.harness_review import ReviewHarness, STEPS, PERSONA_A, PERSONA_B, PERSONA_C
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
    assert STEPS == ("R0", "R1", "R2", "R3", "done")


def test_personas_defined():
    assert "법률 검토" in PERSONA_A or "법률" in PERSONA_A
    assert "동등성" in PERSONA_B
    assert "통합" in PERSONA_C or "reconciler" in PERSONA_C.lower()


def test_review_harness_initial_state(tmp_path):
    store = make_local_store(tmp_path)
    _setup_run(store)
    h = ReviewHarness(vision_provider=FakeProvider())
    # _state.json 부재 시 기본값
    state = h._load_state(store, "r1")
    assert state["step"] == "R0"
    assert state["acknowledged"] is False


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
    assert state["step"] == "R3"


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
    assert state["step"] == "R3"
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
