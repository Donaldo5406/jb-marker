"""파이프라인 프리뷰 배선(Plan 3 Task 2, spec §2) — S1/S2b/S2a/remediate가
``rough/preview.html``(mime text/html)를 순수 가산으로 기록하고, 렌더 실패는 비차단.

layout_preview 렌더러 자체의 단위 테스트는 test_layout_preview.py. 여기서는 스텝이
렌더러를 올바른 지점에서 호출하고, 실패해도 스텝이 죽지 않는지(계약)를 검증한다.
"""
import json

from app.gateway.harness import HarnessRequest
from app.gateway.harness_design import DesignHarness
from app.providers.base import ProviderResponse
from app.providers.fake import FakeProvider
from app.vfs.local import LocalVfsStore

PREVIEW = "/r1/design/rough/preview.html"
SPEC = "/r1/design/rough/layout.spec.json"


def _store(tmp_path):
    s = LocalVfsStore(storage_dir=str(tmp_path))
    s.create_run("r1", languages=["ko"])
    s.put("/r1/brainstorming/plan.md",
          "---\ncreative_direction:\n  palette: [\"#0A84FF\"]\n  font: Inter\n  aspect: \"1:1\"\n"
          "factsheet:\n  interest_rate: \"연 3.5%\"\n  product_name: \"든든적금\"\n"
          "material_matrix: [{channel: instagram, lang: ko}]\nlanguages: [ko]\n---\n본문",
          source="marker", mime="text/markdown")
    return s


def _req(action="advance", prompt=""):
    return HarnessRequest(run_id="r1", studio="design", user_prompt=prompt,
                          provider="fake", is_marker=True, action=action)


class _SpecProvider(FakeProvider):
    """S1이 파싱할 layout_spec을 반환 — 헤드라인에 악성 태그를 넣어 escape도 검증."""

    def complete(self, messages, *, model=None, system=None, tools=None, **kw):
        doc = {"reply": "러프 완성", "ready": True, "layout_spec": {
            "aspect": "1:1", "bg_color": "#FFFFFF", "visual_concept": "블루 그라디언트",
            "slots": [{"role": "headline", "bbox": {"x": 80, "y": 120, "w": 920, "h": 200},
                       "z": 2, "copy_key": "headline", "color": "#0B1324"}],
            "copy": {"ko": {"headline": "<script>alert(1)</script>든든한 적금"}}}}
        return ProviderResponse(text=json.dumps(doc, ensure_ascii=False), model=model)


def test_s1_writes_preview_html_text_and_escapes_script(tmp_path):
    s = _store(tmp_path)
    h = DesignHarness(image_provider=FakeProvider())
    h.handle_turn(_req(), provider=_SpecProvider(), store=s)   # S0→S1
    node = s.get(PREVIEW)
    assert node is not None, "S1 후 rough/preview.html 노드가 있어야 함"
    assert node.mime == "text/html"
    html = node.content_text
    assert html and html.lstrip().startswith("<!doctype html")
    # 악성 카피는 escape되어 실행 가능한 <script 태그로 새지 않아야 한다.
    assert "<script" not in html
    assert "&lt;script&gt;" in html
    # S1은 visual 없음 → 배경 이미지 인라인 없음.
    assert "data:image" not in html


def test_s2a_baked_preview_inlines_visual(tmp_path, monkeypatch):
    monkeypatch.delenv("RICH_VECTOR_CHROME", raising=False)   # baked 경로 강제
    s = _store(tmp_path)
    s.put("/r1/design/_state.json", json.dumps(
        {"step": "S2a", "confirmed": {"S0": True, "S1": True}, "bypass": {},
         "languages": ["ko"], "pending_ask": None}),
        source="marker", mime="application/json")
    s.put(SPEC, json.dumps({"visual_concept": "블루 그라디언트", "aspect": "1:1",
                            "copy": {"ko": {"headline": "든든한 적금"}}}),
          source="marker", mime="application/json")
    h = DesignHarness(image_provider=FakeProvider())
    h.handle_turn(_req(action="advance"), provider=FakeProvider(), store=s)
    node = s.get(PREVIEW)
    assert node is not None and node.mime == "text/html"
    # baked 경로는 v1.png 바이트를 프리뷰 배경으로 인라인한다.
    assert "data:image" in node.content_text


def test_preview_render_failure_is_non_blocking(tmp_path, monkeypatch):
    # 렌더러가 예외를 던져도 스텝은 정상 완료(HarnessResult 반환)해야 한다(spec §2 비차단).
    def _boom(*a, **kw):
        raise RuntimeError("render boom")
    monkeypatch.setattr("app.gateway.design.steps.build_layout_mock_html", _boom)
    s = _store(tmp_path)
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(), provider=_SpecProvider(), store=s)   # S0→S1, no raise
    assert res.meta.get("step") == "S1"          # 스텝은 정상 완료
    assert s.get(SPEC) is not None               # 스텝 본연의 산출물은 기록됨
    assert s.get(PREVIEW) is None                # 프리뷰만 조용히 skip(비차단)


def test_remediate_updates_preview(tmp_path, monkeypatch):
    monkeypatch.delenv("RICH_VECTOR_CHROME", raising=False)   # baked 재베이크 경로
    s = _store(tmp_path)
    s.put("/r1/design/_state.json", json.dumps(
        {"step": "done", "gate": None, "confirmed": {}, "bypass": {},
         "languages": ["ko"], "pending_ask": None}),
        source="marker", mime="application/json")
    s.put(SPEC, json.dumps({"aspect": "1:1", "visual_concept": "블루 그라디언트",
                            "slots": [{"role": "headline", "copy_key": "headline",
                                       "bbox": {"x": 0, "y": 0, "w": 900, "h": 120}}],
                            "copy": {"ko": {"headline": "업계 최고 4.0% 적금"}}}),
          source="marker", mime="application/json")
    h = DesignHarness(image_provider=FakeProvider())
    # done 상태 + action 없음 + 교정 토큰 → _remediate_copy 진입.
    req = HarnessRequest(run_id="r1", studio="design",
                         user_prompt="리뷰 지적을 반영해 고지를 교정해줘",
                         provider="fake", is_marker=True, action="")
    res = h.handle_turn(req, provider=FakeProvider(), store=s)
    assert res.meta.get("remediated") is True
    node = s.get(PREVIEW)
    assert node is not None and node.mime == "text/html"
    # baked 모드 재베이크가 새 v1.png를 프리뷰에 인라인한다(교정 후 갱신 확인).
    assert "data:image" in node.content_text
