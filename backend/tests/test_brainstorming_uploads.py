"""Brain 업로드 소비 — Stage A/B system 프롬프트에 [사용자 제공 자료] 주입(가산적)."""
import json

from app.gateway.harness import HarnessRequest
from app.gateway.harness_brainstorming import BrainstormingHarness
from app.providers.base import ProviderResponse
from app.vfs.factory import make_local_store


def _req(prompt="캠페인 시작"):
    return HarnessRequest(run_id="rb", studio="brainstorming", user_prompt=prompt,
                          provider="fake", is_marker=True)


def _reply(text="ok"):
    return ProviderResponse(text=json.dumps({"reply": text}, ensure_ascii=False), model="x")


def test_stage_a_injects_uploads_block(tmp_path, make_scripted):
    store = make_local_store(tmp_path)
    store.create_run("rb")
    store.put("/rb/brainstorming/uploads/market.md", "시장 자료 본문",
              source="user", mime="text/markdown")
    sp = make_scripted(complete_responses=[_reply()])
    BrainstormingHarness().handle_turn(_req(), provider=sp, store=store)
    system = sp.calls_complete[0]["system"]
    assert "[사용자 제공 자료]" in system
    assert "market.md" in system and "시장 자료 본문" in system


def test_stage_a_without_uploads_no_block(tmp_path, make_scripted):
    store = make_local_store(tmp_path)
    store.create_run("rb")
    sp = make_scripted(complete_responses=[_reply()])
    BrainstormingHarness().handle_turn(_req(), provider=sp, store=store)
    assert "[사용자 제공 자료]" not in sp.calls_complete[0]["system"]


def test_stage_b_injects_uploads_block(tmp_path, make_scripted):
    store = make_local_store(tmp_path)
    store.create_run("rb")
    store.put("/rb/brainstorming/uploads/product.md", "상품 자료 본문",
              source="user", mime="text/markdown")
    store.put("/rb/brainstorming/spec.md", "---\nmedium: image\n---\n# spec",
              source="marker", mime="text/markdown")
    # stage B로 상태 강제(스테이지 전이 로직 비경유 — 주입만 검증)
    h = BrainstormingHarness()
    state = h._load_state(store, "rb")
    state["stage"] = "B"
    h._save_state(store, "rb", state)
    sp = make_scripted(complete_responses=[_reply()])
    h.handle_turn(_req("계획 만들어줘"), provider=sp, store=store)
    system = sp.calls_complete[0]["system"]
    assert "[사용자 제공 자료]" in system and "상품 자료 본문" in system
