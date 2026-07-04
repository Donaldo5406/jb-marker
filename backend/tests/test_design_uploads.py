"""Design 업로드 소비 — S1 프롬프트에 [사용자 제공 자료] 주입(가산적)."""
import json

from app.gateway.design.steps import S1Rough
from app.gateway.harness import HarnessRequest
from app.gateway.pipeline import StepContext
from app.providers.base import ProviderResponse
from app.vfs.factory import make_local_store


def _layout_reply():
    return ProviderResponse(
        text=json.dumps({"reply": "러프 완성",
                         "layout_spec": {"slots": [], "copy": {}, "aspect": "1:1"}},
                        ensure_ascii=False), model="x")


def _ctx(store, provider):
    req = HarnessRequest(run_id="r1", studio="design", user_prompt="러프 시작",
                          provider="fake", is_marker=True)
    return StepContext(req=req, provider=provider, store=store,
                       state={"languages": ["ko"]}, base="/r1/design")


def test_s1_injects_uploads_block(tmp_path, make_scripted):
    store = make_local_store(tmp_path)
    store.create_run("r1")
    store.put("/r1/design/uploads/brand-guide.md", "브랜드 가이드 본문",
              source="user", mime="text/markdown")
    sp = make_scripted(complete_responses=[_layout_reply()])
    S1Rough().run(_ctx(store, sp))
    system = sp.calls_complete[0]["system"]
    assert "[사용자 제공 자료]" in system and "브랜드 가이드 본문" in system


def test_s1_without_uploads_no_block(tmp_path, make_scripted):
    store = make_local_store(tmp_path)
    store.create_run("r1")
    sp = make_scripted(complete_responses=[_layout_reply()])
    S1Rough().run(_ctx(store, sp))
    assert "[사용자 제공 자료]" not in sp.calls_complete[0]["system"]
