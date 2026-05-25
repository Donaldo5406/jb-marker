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
