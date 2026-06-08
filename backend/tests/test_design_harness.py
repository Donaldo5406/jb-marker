import json
import re

from app.gateway.harness import HarnessRequest
from app.gateway.harness_design import DesignHarness
from app.providers.fake import FakeProvider
from app.vfs.local import LocalVfsStore


def _store(tmp_path):
    s = LocalVfsStore(storage_dir=str(tmp_path))
    s.create_run("r1", languages=["ko"])
    s.put("/r1/brainstorming/plan.md",
          "---\ncreative_direction:\n  palette: [\"#0A84FF\"]\n  font: Inter\n  aspect: \"1:1\"\n"
          "factsheet:\n  rate: \"연 3.5%\"\n"
          "material_matrix: [{channel: instagram, lang: ko}]\nlanguages: [ko]\n---\n본문",
          source="marker", mime="text/markdown")
    return s


def _req(action="advance", prompt=""):
    return HarnessRequest(run_id="r1", studio="design", user_prompt=prompt,
                          provider="fake", is_marker=True, action=action)


def test_s0_parses_plan_into_tokens_and_state(tmp_path):
    s = _store(tmp_path)
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(), provider=FakeProvider(), store=s)
    tok = json.loads(s.get("/r1/design/design-system/tokens.json").content_text)
    assert tok["aspect"] == "1:1" and "#0A84FF" in tok["palette"]
    st = json.loads(s.get("/r1/design/_state.json").content_text)
    assert st["step"] == "S1"          # S0→S1 체인 후 S1 게이트
    assert st["gate"] == "S1"
    assert res.meta["step"] == "S1"
    assert st["languages"] == ["ko"]


def test_state_default_step_s0(tmp_path):
    s = _store(tmp_path)
    h = DesignHarness(image_provider=FakeProvider())
    st = h._load_state(s, "r1")
    assert st["step"] == "S0"


def test_s0_persists_material_matrix(tmp_path):
    s = _store(tmp_path)
    h = DesignHarness(image_provider=FakeProvider())
    h.handle_turn(_req(), provider=FakeProvider(), store=s)
    mm = json.loads(s.get("/r1/design/_material_matrix.json").content_text)
    assert mm and mm[0]["channel"] == "instagram"


# --- FIX: creative_direction 서술형(실 브레인스토밍) 형식 수용 + aspect 추론 ---

def test_aspect_from_matrix():
    from app.gateway.harness_design import _aspect_from_matrix
    assert _aspect_from_matrix([{"size": "1080×1920 (9:16)"}]) == "9:16"   # 명시 비율 우선
    assert _aspect_from_matrix([{"size": "1080×1080 (정방형)"}]) == "1:1"  # 픽셀→근사
    assert _aspect_from_matrix([{"size": "1080x1350"}]) == "4:5"           # 세로 포스터
    assert _aspect_from_matrix([{"format": "배너"}]) is None               # 단서 없음
    assert _aspect_from_matrix([]) is None


def test_s0_accepts_descriptive_creative_direction(tmp_path):
    # 실 브레인스토밍이 쓰는 서술형 creative_direction → 빈 tokens 대신 브랜드 방향 보존.
    s = _store(tmp_path)
    s.put("/r1/brainstorming/plan.md",
          "---\ncreative_direction:\n"
          "  concept: \"일상 속 3분 재테크\"\n"
          "  color_palette: \"딥 네이비 + 라이트 민트\"\n"
          "  typography: \"헤드라인 굵게, 본문 산세리프\"\n"
          "material_matrix: [{channel: instagram, size: \"1080×1080\"}]\n"
          "languages: [ko]\n---\n본문",
          source="marker", mime="text/markdown")
    h = DesignHarness(image_provider=FakeProvider())
    h.handle_turn(_req(), provider=FakeProvider(), store=s)
    tok = json.loads(s.get("/r1/design/design-system/tokens.json").content_text)
    assert tok["color_palette"] == "딥 네이비 + 라이트 민트"   # 서술형 팔레트 보존
    assert tok["font"] == "헤드라인 굵게, 본문 산세리프"        # typography → font 폴백
    assert tok["concept"] == "일상 속 3분 재테크"
    assert tok["aspect"] == "1:1"   # creative_direction에 aspect 없음 → matrix에서 추론


def test_s0_structured_creative_direction_still_works(tmp_path):
    # 구조형(데모 형식) 회귀 가드 — palette/font/aspect 그대로 보존.
    s = _store(tmp_path)   # _store의 plan.md는 palette/font/aspect 구조형
    h = DesignHarness(image_provider=FakeProvider())
    h.handle_turn(_req(), provider=FakeProvider(), store=s)
    tok = json.loads(s.get("/r1/design/design-system/tokens.json").content_text)
    assert "#0A84FF" in tok["palette"] and tok["font"] == "Inter" and tok["aspect"] == "1:1"


# --- Task 6: few-shot 번들 + S1 Rough ---


def _advance_to(store, h, step):
    st = json.loads(store.get("/r1/design/_state.json").content_text) \
         if store.get("/r1/design/_state.json") else None
    return st


def test_load_references_returns_bundled_specs(tmp_path):
    h = DesignHarness(image_provider=FakeProvider())
    refs = h._load_references()
    assert len(refs) >= 2
    assert any(r["kind"] == "poster" for r in refs)


def test_s1_writes_layout_spec_from_llm(tmp_path):
    s = _store(tmp_path)
    h = DesignHarness(image_provider=FakeProvider())

    class SpecProvider(FakeProvider):
        def complete(self, messages, *, model, system=None, tools=None, **kw):
            from app.providers.base import ProviderResponse
            doc = {"reply": "러프 완성", "layout_spec": {"aspect": "1:1", "grid": {"cols": 12},
                   "visual_concept": "블루 그라디언트", "slots": [{"role": "headline",
                   "bbox": {"x": 80, "y": 120, "w": 920, "h": 200}, "z": 2, "copy_key": "headline"}],
                   "copy": {"ko": {"headline": "든든한 적금"}}}, "ready": True}
            return ProviderResponse(text=json.dumps(doc, ensure_ascii=False), model=model)

    res = h.handle_turn(_req(), provider=SpecProvider(), store=s)   # S0→S1(SpecProvider)
    spec = json.loads(s.get("/r1/design/rough/layout.spec.json").content_text)
    assert spec["visual_concept"] == "블루 그라디언트"
    st = json.loads(s.get("/r1/design/_state.json").content_text)
    assert st["step"] == "S1" and st["gate"] == "S1"   # S1 게이트 정지


# --- Task 7: S2a 비주얼(Nano Banana → components/visual) ---


def test_s2a_generates_visual_blob_via_image_provider(tmp_path):
    s = _store(tmp_path)
    h = DesignHarness(image_provider=FakeProvider())
    s.put("/r1/design/_state.json", json.dumps(
        {"step": "S2a", "confirmed": {"S0": True, "S1": True}, "bypass": {},
         "languages": ["ko"], "pending_ask": None}),
        source="marker", mime="application/json")
    s.put("/r1/design/rough/layout.spec.json",
          json.dumps({"visual_concept": "블루 그라디언트", "aspect": "1:1"}),
          source="marker", mime="application/json")
    res = h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)
    nodes = s.list("/r1/design/design-system/components/visual")
    assert any(n.path.endswith(".png") for n in nodes)
    assert json.loads(s.get("/r1/design/_state.json").content_text)["step"] == "S2a"
    assert json.loads(s.get("/r1/design/_state.json").content_text)["gate"] == "S2a"


# --- Task 8: S2b 카피·타이포 + grounding 검증 ---


def test_s2b_writes_copy_and_flags_ungrounded(tmp_path):
    s = _store(tmp_path)
    s.put("/r1/design/_state.json", json.dumps(
        {"step":"S2b","confirmed":{},"bypass":{},"languages":["ko"],"pending_ask":None}),
        source="marker", mime="application/json")
    s.put("/r1/design/rough/layout.spec.json",
          json.dumps({"copy":{"ko":{"headline":"연 9.9% 특별적금","cta":"가입"}}}),
          source="marker", mime="application/json")
    h = DesignHarness(image_provider=FakeProvider())
    class CopyProvider(FakeProvider):
        def complete(self, messages, *, model, system=None, tools=None, **kw):
            from app.providers.base import ProviderResponse
            return ProviderResponse(text=json.dumps({"copy":{"ko":{
                "headline":"연 9.9% 특별적금","body":"","cta":"가입"}}}), model=model)
    res = h.handle_turn(_req(action="advance"), provider=CopyProvider(), store=s)
    hl = s.get("/r1/design/design-system/components/headline/ko.txt")
    assert hl is not None
    assert "9.9%" in (res.meta.get("ungrounded") or [])


# --- Task 9: S2c 브랜드·컴플라이언스 컴포넌트 ---


def test_s2c_writes_logo_disclosure_and_ai_notice(tmp_path):
    s = _store(tmp_path)
    s.put("/r1/design/_state.json", json.dumps(
        {"step":"S2c","confirmed":{},"bypass":{},"languages":["ko"],"pending_ask":None}),
        source="marker", mime="application/json")
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)
    disc = s.get("/r1/design/design-system/components/disclosure/ko.txt")
    assert disc is not None and "AI" in disc.content_text
    st = json.loads(s.get("/r1/design/_state.json").content_text)
    assert st["step"] == "S2c" and st["gate"] == "S2c"


# --- Task 10: S3 크리틱 루브릭 + metadata.md + step_status(done) ---


def test_critic_returns_7_scores_and_threshold(tmp_path):
    h = DesignHarness(image_provider=FakeProvider())
    scores = h.critic({"hierarchy":4,"grid":4,"whitespace":4,"cta":4,
                       "compliance":4,"copy_visual":4,"brand":4})
    assert scores["pass"] is True
    bad = h.critic({"hierarchy":1,"grid":4,"whitespace":4,"cta":4,
                    "compliance":4,"copy_visual":4,"brand":4})
    assert bad["pass"] is False


def test_s3_writes_metadata_and_marks_done(tmp_path):
    s = _store(tmp_path)
    s.put("/r1/design/_state.json", json.dumps(
        {"step":"S3","confirmed":{},"bypass":{"S3":True},"languages":["ko"],
         "pending_ask":None}), source="marker", mime="application/json")
    s.put("/r1/design/rough/layout.spec.json",
          json.dumps({"copy":{"ko":{"headline":"든든한 적금"}}}),
          source="marker", mime="application/json")
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(action="confirm"), provider=FakeProvider(), store=s)
    assert s.get("/r1/design/metadata.md") is not None
    assert s.get_manifest("r1").step_status["design"] == "done"


def test_s3_metadata_includes_body_key(tmp_path):
    """metadata.md는 headline/body/cta를 모두 표기해야 한다(copy 키는 'body'이며 'sub' 아님).
    기존 루프가 'sub'를 찾아 body가 누락됐다(spec T1)."""
    s = _store(tmp_path)
    s.put("/r1/design/_state.json", json.dumps(
        {"step": "S3", "confirmed": {}, "bypass": {"S3": True}, "languages": ["ko"],
         "pending_ask": None}), source="marker", mime="application/json")
    s.put("/r1/design/rough/layout.spec.json",
          json.dumps({"copy": {"ko": {"headline": "든든한 적금", "body": "12개월 만기 100만원부터", "cta": "가입하기"}}}),
          source="marker", mime="application/json")
    h = DesignHarness(image_provider=FakeProvider())
    h.handle_turn(_req(action="confirm"), provider=FakeProvider(), store=s)
    md = s.get("/r1/design/metadata.md").content_text
    assert "든든한 적금" in md   # headline
    assert "12개월 만기 100만원부터" in md   # body (회귀 방지: 'sub'면 누락됨)
    assert "가입하기" in md   # cta


def test_s3_metadata_includes_visual_compliance(tmp_path):
    """#3: metadata.md에 시각 적법성 측정값(visual_compliance) 블록이 기록돼야 한다."""
    s = _store(tmp_path)
    s.put("/r1/design/_state.json", json.dumps(
        {"step": "S3", "confirmed": {}, "bypass": {"S3": True}, "languages": ["ko"],
         "pending_ask": None}), source="marker", mime="application/json")
    s.put("/r1/design/rough/layout.spec.json", json.dumps({
        "bg_color": "#F2EFE9",
        "slots": [
            {"role": "headline", "font_px": 72, "color": "#0B1324"},
            {"role": "disclosure", "font_px": 26, "color": "#3A3A3A"},
        ],
        "copy": {"ko": {"headline": "h", "body": "b", "cta": "c",
                        "disclosure": "예금자보호법에 따라 5천만원까지 보호"}},
    }), source="marker", mime="application/json")
    h = DesignHarness(image_provider=FakeProvider())
    h.handle_turn(_req(action="confirm"), provider=FakeProvider(), store=s)
    md = s.get("/r1/design/metadata.md").content_text
    assert "시각 적법성(visual_compliance)" in md
    assert "disclosure_font_px: 26" in md
    assert "disclosure_contrast:" in md
    assert "passed: True" in md   # 적법 레이아웃(26/72=36% ≥ 30%, 대비 ≥ 4.5)


def test_done_step_is_idempotent_no_error(tmp_path):
    s = _store(tmp_path)
    s.put("/r1/design/_state.json", json.dumps(
        {"step":"done","confirmed":{},"bypass":{},"languages":["ko"],"pending_ask":None}),
        source="marker", mime="application/json")
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)
    assert res.meta.get("step") == "done"   # no exception


def test_parse_json_returns_empty_on_non_json_with_braces(tmp_path):
    # 정규식이 비-JSON 중괄호 조각(예: 프롬프트 echo)을 매칭해도 폴백은 raise하지 않아야 함
    h = DesignHarness(image_provider=FakeProvider())
    assert h._parse_json("설명 {role: bbox, not: valid json}") == {}
    assert h._parse_json("") == {}
    assert h._parse_json("그냥 텍스트") == {}
    assert h._parse_json('앞 {"a": 1} 뒤') == {"a": 1}   # 유효 JSON 부분은 추출


def test_s1_does_not_crash_with_plain_fake_provider(tmp_path):
    s = _store(tmp_path)
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(), provider=FakeProvider(), store=s)   # S0→S1, gate
    assert res.meta.get("step") == "S1"
    spec = json.loads(s.get("/r1/design/rough/layout.spec.json").content_text)
    assert isinstance(spec, dict)
    st = json.loads(s.get("/r1/design/_state.json").content_text)
    assert st["step"] == "S1" and st["gate"] == "S1"


def test_full_pipeline_with_fake_provider_completes(tmp_path):
    # 오프라인(fake) 전체 완주: S0~S3 → done + step_status, 크래시 없음
    s = _store(tmp_path)
    h = DesignHarness(image_provider=FakeProvider())
    for _ in range(7):
        h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)
    assert json.loads(s.get("/r1/design/_state.json").content_text)["step"] == "done"
    assert s.get_manifest("r1").step_status["design"] == "done"
    assert s.get("/r1/design/metadata.md") is not None


# --- Task 17: confirm 게이트 bypass(자동 진행) 토글 ---


def test_s3_bypass_auto_passes_on_weak_critic(tmp_path):
    s = _store(tmp_path)
    s.put("/r1/design/_state.json", json.dumps(
        {"step":"S3","confirmed":{},"bypass":{"S3":True},"languages":["ko"],
         "pending_ask":None}), source="marker", mime="application/json")
    s.put("/r1/design/rough/layout.spec.json", json.dumps({"copy":{"ko":{}}}),
          source="marker", mime="application/json")
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)
    assert s.get_manifest("r1").step_status["design"] == "done"


# bypass_map 검증은 test_design_gate/test_server_design로 이동


# --- Task 19 FIX A (M8): image generation fake fallback ---


def test_s2a_falls_back_to_fake_png_when_image_provider_raises(tmp_path):
    s = _store(tmp_path)

    class BoomImageProvider(FakeProvider):
        def generate_image(self, prompt, *, aspect="1:1"):
            raise RuntimeError("no api key")

    s.put("/r1/design/_state.json", json.dumps(
        {"step": "S2a", "confirmed": {"S0": True, "S1": True}, "bypass": {},
         "languages": ["ko"], "pending_ask": None}),
        source="marker", mime="application/json")
    s.put("/r1/design/rough/layout.spec.json",
          json.dumps({"visual_concept": "블루 그라디언트", "aspect": "1:1"}),
          source="marker", mime="application/json")
    h = DesignHarness(image_provider=BoomImageProvider())
    res = h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)  # no raise
    png = s.get("/r1/design/design-system/components/visual/v1.png")
    assert png is not None and png.blob  # valid PNG written
    assert res.meta.get("image_fallback") is True
    assert json.loads(s.get("/r1/design/_state.json").content_text)["step"] == "S2a"


def test_s2a_records_no_fallback_on_success(tmp_path):
    s = _store(tmp_path)
    s.put("/r1/design/_state.json", json.dumps(
        {"step": "S2a", "confirmed": {"S0": True, "S1": True}, "bypass": {},
         "languages": ["ko"], "pending_ask": None}),
        source="marker", mime="application/json")
    s.put("/r1/design/rough/layout.spec.json",
          json.dumps({"visual_concept": "블루 그라디언트", "aspect": "1:1"}),
          source="marker", mime="application/json")
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)
    assert res.meta.get("image_fallback") is False


# --- Task 19 FIX B: S2b writes refined copy back into layout.spec.json ---


def test_s2b_merges_copy_into_layout_spec_preserving_rest(tmp_path):
    s = _store(tmp_path)
    s.put("/r1/design/_state.json", json.dumps(
        {"step": "S2b", "confirmed": {}, "bypass": {}, "languages": ["ko"],
         "pending_ask": None}), source="marker", mime="application/json")
    s.put("/r1/design/rough/layout.spec.json", json.dumps({
        "aspect": "1:1", "visual_concept": "블루 그라디언트",
        "slots": [{"role": "headline", "copy_key": "headline"}],
        "copy": {"ko": {"headline": "구버전", "body": "old"}}}),
        source="marker", mime="application/json")
    h = DesignHarness(image_provider=FakeProvider())

    class CopyProvider(FakeProvider):
        def complete(self, messages, *, model, system=None, tools=None, **kw):
            from app.providers.base import ProviderResponse
            return ProviderResponse(text=json.dumps({"copy": {"ko": {
                "headline": "든든한 적금", "body": "", "cta": "가입"}}}), model=model)

    h.handle_turn(_req(action="advance"), provider=CopyProvider(), store=s)
    spec = json.loads(s.get("/r1/design/rough/layout.spec.json").content_text)
    assert spec["copy"]["ko"]["headline"] == "든든한 적금"   # refined copy merged
    assert spec["visual_concept"] == "블루 그라디언트"       # rest preserved
    assert spec["slots"][0]["role"] == "headline"
    # .txt component still written
    assert s.get("/r1/design/design-system/components/headline/ko.txt") is not None


# --- Task 19 FIX C (M7): _s3_final executes critic (advisory, non-blocking) ---


def test_s3_runs_and_records_critic_without_blocking(tmp_path):
    s = _store(tmp_path)
    s.put("/r1/design/_state.json", json.dumps(
        {"step": "S3", "confirmed": {}, "bypass": {}, "languages": ["ko"],
         "pending_ask": None}), source="marker", mime="application/json")
    s.put("/r1/design/rough/layout.spec.json",
          json.dumps({"copy": {"ko": {"headline": "든든한 적금"}}}),
          source="marker", mime="application/json")
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)
    assert res.meta.get("critic", {}).get("pass") in (True, False)
    md = s.get("/r1/design/metadata.md").content_text
    assert "크리틱" in md
    st = json.loads(s.get("/r1/design/_state.json").content_text)
    assert st["step"] == "S3" and st["gate"] == "S3"   # S3 게이트 정지(critic은 자문 보존)


# --- Task 19 FIX D (I5): localized AI-generated notice per language ---


def test_s2c_localizes_disclosure_and_stages_vi_zh_missing(tmp_path):
    """T2: 법령 고지는 표시문(번역)이 있는 언어(ko·en)에만 부착, 없는 언어(vi·zh)는 누락.
    → vi/zh 포스터 한글 0 + 예금자보호 고지 누락(spec §2 위반#4 스테이징). en엔 영문 고지."""
    s = _store(tmp_path)
    s.put("/r1/brainstorming/plan.md",
          "---\ndisclosures: [예금자보호법에 따라 5천만원까지 보호]\n"
          "languages: [ko, en, vi, zh]\n---\n본문",
          source="marker", mime="text/markdown")
    s.put("/r1/design/_state.json", json.dumps(
        {"step": "S2c", "confirmed": {}, "bypass": {},
         "languages": ["ko", "en", "vi", "zh"], "pending_ask": None}),
        source="marker", mime="application/json")
    h = DesignHarness(image_provider=FakeProvider())
    h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)
    ko = s.get("/r1/design/design-system/components/disclosure/ko.txt").content_text
    en = s.get("/r1/design/design-system/components/disclosure/en.txt").content_text
    vi = s.get("/r1/design/design-system/components/disclosure/vi.txt").content_text
    zh = s.get("/r1/design/design-system/components/disclosure/zh.txt").content_text
    assert "예금자보호" in ko                                  # ko: 한국어 법령 고지
    assert "Protected up to" in en                            # en: 영문 법령 고지(표시문 보유)
    assert "예금자보호" not in en                              # en에 한국어 미혼입
    assert "Protected up to" not in vi and "Protected up to" not in zh  # vi/zh: 고지 누락(위반#4)
    H = re.compile(r"[가-힣]")
    assert not H.search(en), f"en 한글 혼입: {en!r}"
    assert not H.search(vi), f"vi 한글 혼입: {vi!r}"            # vi 현지화 고지만(한글 0)
    assert not H.search(zh), f"zh 한글 혼입: {zh!r}"            # zh 현지화 고지(zh NOTICE)


def test_s2c_ko_keeps_disclosure_without_display_mapping(tmp_path):
    """실 캠페인 회귀 가드: plan.md의 disclosure가 DISCLOSURE_DISPLAY 매핑에 없어도
    ko 포스터에는 원문 고지가 부착돼야 한다. (표시문 정확일치에 묶여 임의 disclosure가
    ko 포스터에서 통째 사라지던 위험 차단.) 외국어는 무번역 누락 유지 → R2가 잡는다."""
    s = _store(tmp_path)
    s.put("/r1/brainstorming/plan.md",
          "---\ndisclosures: [투자원금 손실이 발생할 수 있습니다]\n"
          "languages: [ko, en]\n---\n본문",
          source="marker", mime="text/markdown")
    s.put("/r1/design/_state.json", json.dumps(
        {"step": "S2c", "confirmed": {}, "bypass": {},
         "languages": ["ko", "en"], "pending_ask": None}),
        source="marker", mime="application/json")
    h = DesignHarness(image_provider=FakeProvider())
    h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)
    ko = s.get("/r1/design/design-system/components/disclosure/ko.txt").content_text
    en = s.get("/r1/design/design-system/components/disclosure/en.txt").content_text
    assert "투자원금 손실" in ko                 # ko: 매핑 없어도 원문 고지 부착
    assert "투자원금" not in en                   # en: 무번역 → 누락(R2 검출 대상)


def test_s2c_localizes_ai_notice_per_language(tmp_path):
    s = _store(tmp_path)
    s.put("/r1/design/_state.json", json.dumps(
        {"step": "S2c", "confirmed": {}, "bypass": {}, "languages": ["ko", "en"],
         "pending_ask": None}), source="marker", mime="application/json")
    h = DesignHarness(image_provider=FakeProvider())
    h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)
    en = s.get("/r1/design/design-system/components/disclosure/en.txt").content_text
    ko = s.get("/r1/design/design-system/components/disclosure/ko.txt").content_text
    assert "AI" in en and "generated by AI" in en
    assert "AI로 생성되었습니다" in ko


# --- Task 21 FIX 3: S2c merges AI/disclosure notice into layout.spec.json copy ---


def test_s2c_merges_disclosure_into_layout_spec_preserving_rest(tmp_path):
    s = _store(tmp_path)
    s.put("/r1/design/_state.json", json.dumps(
        {"step": "S2c", "confirmed": {}, "bypass": {}, "languages": ["ko", "en"],
         "pending_ask": None}), source="marker", mime="application/json")
    s.put("/r1/design/rough/layout.spec.json", json.dumps({
        "aspect": "1:1", "visual_concept": "블루 그라디언트",
        "slots": [{"role": "headline", "copy_key": "headline"}],
        "copy": {"ko": {"headline": "든든한 적금"}}}),
        source="marker", mime="application/json")
    h = DesignHarness(image_provider=FakeProvider())
    h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)
    spec = json.loads(s.get("/r1/design/rough/layout.spec.json").content_text)
    assert "AI" in spec["copy"]["ko"]["disclosure"]   # Korean AI notice merged
    assert "AI" in spec["copy"]["en"]["disclosure"]   # English AI notice merged
    assert spec["copy"]["ko"]["headline"] == "든든한 적금"   # pre-existing copy preserved
    assert spec["visual_concept"] == "블루 그라디언트"       # rest preserved
    assert spec["slots"][0]["role"] == "headline"


# --- Task 19 FIX E (I2): regenerate re-runs the previous completed step ---


def test_regenerate_with_no_gate_runs_pipeline(tmp_path):
    s = _store(tmp_path)   # state default S0, gate None
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(action="regenerate"), provider=FakeProvider(), store=s)
    # 게이트 없음 + regenerate → (c) 루프 진입(S0→S1 게이트)
    st = json.loads(s.get("/r1/design/_state.json").content_text)
    assert st["step"] == "S1" and st["gate"] == "S1"


# --- FIX A: 실 LLM의 객체 리스트 languages → 문자열 코드 정규화(unhashable 크래시 방지) ---

_PLAN_OBJ_LANGS = (
    "---\n"
    "creative_direction:\n  palette: [\"#0A84FF\"]\n  font: Inter\n  aspect: \"1:1\"\n"
    "factsheet:\n  rate: \"연 3.5%\"\n"
    "disclosures:\n  - \"예금자보호법에 따라 5천만원까지 보호\"\n"
    "material_matrix: [{channel: instagram, lang: ko}]\n"
    "languages:\n"
    "  - code: ko\n    label: 한국어\n    primary: true\n"
    "  - code: en\n    label: English\n"
    "---\n본문")


def _bypass_all_req():
    return HarnessRequest(run_id="r1", studio="design", user_prompt="",
                          provider="fake", is_marker=True, action="advance",
                          bypass_map={s: True for s in ("S1", "S2a", "S2b", "S2c", "S3")})


def test_s0_normalizes_object_list_languages(tmp_path):
    s = _store(tmp_path)
    s.put("/r1/brainstorming/plan.md", _PLAN_OBJ_LANGS, source="marker", mime="text/markdown")
    h = DesignHarness(image_provider=FakeProvider())
    h.handle_turn(_req(), provider=FakeProvider(), store=s)
    st = json.loads(s.get("/r1/design/_state.json").content_text)
    assert st["languages"] == ["ko", "en"]   # 객체 → 문자열 코드


def test_object_list_languages_pipeline_does_not_crash(tmp_path):
    # 회귀 가드: 실 Claude의 객체 리스트 languages가 S2c(NOTICES.get)·S3(copy.get)에서
    # unhashable dict로 크래시하던 버그. 정규화 후 done까지 무사 완주해야 한다.
    s = _store(tmp_path)
    s.put("/r1/brainstorming/plan.md", _PLAN_OBJ_LANGS, source="marker", mime="text/markdown")
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_bypass_all_req(), provider=FakeProvider(), store=s)
    st = json.loads(s.get("/r1/design/_state.json").content_text)
    assert st["step"] == "done"
    # 언어별 고지 컴포넌트가 문자열 코드 경로로 생성됨(dict 경로 누수 없음).
    assert s.get("/r1/design/design-system/components/disclosure/ko.txt") is not None
    assert s.get("/r1/design/design-system/components/disclosure/en.txt") is not None
    meta_md = s.get("/r1/design/metadata.md").content_text
    assert "code" not in meta_md.split("# 디자인", 1)[0]  # frontmatter에 dict 누수 없음


# --- FIX B: S1이 LLM의 bbox만으로 font_px를 보강해 R-VIS-1을 실효화 ---


def test_s1_enriches_font_px_from_bbox_when_llm_omits(tmp_path):
    s = _store(tmp_path)
    h = DesignHarness(image_provider=FakeProvider())

    class BboxOnlyProvider(FakeProvider):
        def complete(self, messages, *, model, system=None, tools=None, **kw):
            from app.providers.base import ProviderResponse
            doc = {"reply": "러프", "ready": True, "layout_spec": {"aspect": "1:1",
                   "bg_color": "#FFFFFF", "slots": [
                       {"role": "headline", "bbox": {"x": 0, "y": 0, "w": 900, "h": 120},
                        "z": 2, "copy_key": "headline", "color": "#000000"},
                       {"role": "disclosure", "bbox": {"x": 0, "y": 800, "w": 900, "h": 18},
                        "z": 1, "copy_key": "disclosure", "color": "#000000"}],
                   "copy": {"ko": {"headline": "X", "disclosure": "고지"}}}}
            return ProviderResponse(text=json.dumps(doc, ensure_ascii=False), model=model)

    h.handle_turn(_req(), provider=BboxOnlyProvider(), store=s)   # S0→S1
    spec = json.loads(s.get("/r1/design/rough/layout.spec.json").content_text)
    fonts = {sl["role"]: sl.get("font_px") for sl in spec["slots"]}
    assert fonts["headline"] == 120 and fonts["disclosure"] == 18   # bbox 높이로 보강


# --- FIX C: 이미지 생성 실패 폴백이 1×1 빈 PNG가 아니라 보이는 placeholder ---


def test_s2a_fallback_is_visible_placeholder_not_blank(tmp_path):
    s = _store(tmp_path)

    class BoomImageProvider(FakeProvider):
        def generate_image(self, prompt, *, aspect="1:1"):
            raise RuntimeError("no api key")

    s.put("/r1/design/_state.json", json.dumps(
        {"step": "S2a", "confirmed": {"S0": True, "S1": True}, "bypass": {},
         "languages": ["ko"], "pending_ask": None}),
        source="marker", mime="application/json")
    s.put("/r1/design/rough/layout.spec.json",
          json.dumps({"visual_concept": "블루", "aspect": "4:5"}),
          source="marker", mime="application/json")
    h = DesignHarness(image_provider=BoomImageProvider())
    res = h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)
    png = s.get("/r1/design/design-system/components/visual/v1.png")
    assert png is not None and len(png.blob) > 1000   # 1×1(약 70바이트) 아님
    assert png.blob[:8] == b"\x89PNG\r\n\x1a\n"
    assert res.meta.get("image_fallback") is True
    assert "GOOGLE_API_KEY" in res.text
