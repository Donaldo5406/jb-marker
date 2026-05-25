import json

from app.gateway.harness import HarnessRequest
from app.gateway.harness_design import DesignHarness
from app.providers.fake import FakeProvider
from app.vfs.local import LocalVfsStore


def _store(tmp_path):
    s = LocalVfsStore(storage_dir=str(tmp_path))
    s.create_run("r1", languages=["ko"])
    s.put("/r1/brainstorming/plan.md",
          "---\ncreative_direction:\n  palette: [\"#0A84FF\"]\n  font: Inter\n  aspect: \"1:1\"\n"
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
    assert st["step"] == "S1"
    assert st["languages"] == ["ko"]
    assert res.output_path == "/r1/design/design-system/tokens.json"


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
    h.handle_turn(_req(), provider=FakeProvider(), store=s)  # S0

    class SpecProvider(FakeProvider):
        def complete(self, messages, *, model, system=None, tools=None, **kw):
            from app.providers.base import ProviderResponse
            doc = {"reply": "러프 완성", "layout_spec": {"aspect": "1:1", "grid": {"cols": 12},
                   "visual_concept": "블루 그라디언트", "slots": [{"role": "headline",
                   "bbox": {"x": 80, "y": 120, "w": 920, "h": 200}, "z": 2, "copy_key": "headline"}],
                   "copy": {"ko": {"headline": "든든한 적금"}}}, "ready": True}
            return ProviderResponse(text=json.dumps(doc, ensure_ascii=False), model=model)

    res = h.handle_turn(_req(action="advance"), provider=SpecProvider(), store=s)
    spec = json.loads(s.get("/r1/design/rough/layout.spec.json").content_text)
    assert spec["visual_concept"] == "블루 그라디언트"
    assert json.loads(s.get("/r1/design/_state.json").content_text)["step"] == "S2a"
