"""R3 권장수정 기계용 계약 — revise/recommendations.json (폐루프 D1)."""
import json

from app.gateway.harness import HarnessRequest
from app.gateway.harness_review import ReviewHarness
from app.providers.base import ProviderResponse
from app.vfs.factory import make_local_store

_RECON = ProviderResponse(text=json.dumps({
    "recommendations": [
        {"asset_id": "design/final/vi/main.scene", "lang": "vi", "target": "text",
         "instruction": "[missing_disclosure] 예금자보호 고지 누락 — 카피를 교정하세요.",
         "priority": 1, "related_verdict_ids": ["v1"]},
        {"asset_id": "design/final/ko/main.scene", "lang": "ko", "target": "text",
         "instruction": "[표시광고법] 과장 표현 교정", "priority": 2,
         "related_verdict_ids": ["v2"]},
    ], "conflicts_resolved": []}, ensure_ascii=False), model="x")
_EMPTY_RECON = ProviderResponse(text='{"recommendations":[],"conflicts_resolved":[]}', model="x")


def _r3_state(store, run_id="r1"):
    """R3 직행 상태 셋업 — R0~R2 산출과 무관하게 _r3_reconcile 단독 검증."""
    store.create_run(run_id, languages=["ko", "vi"])
    state = {"step": "R3", "languages": ["ko", "vi"], "matrix": {}, "acknowledged": False,
             "live_unavailable": False, "parse_failed": False, "vision_failed": False,
             "step_failed": "", "vision_skipped": [], "dropped_findings_count": 0,
             "r2_skipped": ""}
    store.put(f"/{run_id}/review/_state.json", json.dumps(state, ensure_ascii=False),
              source="marker", mime="application/json")
    return store


def _req():
    return HarnessRequest(run_id="r1", studio="review", user_prompt="계속",
                          provider="fake", is_marker=True)


def test_r3_persists_recommendations_json(tmp_path, make_scripted):
    store = _r3_state(make_local_store(tmp_path))
    h = ReviewHarness(vision_provider=make_scripted())
    h.handle_turn(_req(), provider=make_scripted(complete_responses=[_RECON]), store=store)
    node = store.get("/r1/review/revise/recommendations.json")
    assert node is not None
    recs = json.loads(node.content_text)
    assert len(recs) == 2
    assert recs[0]["rec_id"].startswith("rec_") and len(recs[0]["rec_id"]) == 12
    assert recs[0]["lang"] == "vi" and recs[0]["priority"] == 1
    # 같은 rec는 .md 파일과 rec_id가 일치(결정론 sha1[:8])
    md_paths = [n.path for n in store.list("/r1/review/revise/text/")]
    assert any(recs[0]["rec_id"] in p for p in md_paths)


def test_r3_no_recommendations_no_json(tmp_path, make_scripted):
    store = _r3_state(make_local_store(tmp_path))
    h = ReviewHarness(vision_provider=make_scripted())
    h.handle_turn(_req(), provider=make_scripted(complete_responses=[_EMPTY_RECON]), store=store)
    assert store.get("/r1/review/revise/recommendations.json") is None
