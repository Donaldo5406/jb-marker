"""Review 업로드 심의 — R0 matrix 등재·R1 비전 심의·게이트 합류·R3 리포트 섹션·무업로드 회귀."""
import json

from app.gateway.harness import HarnessRequest
from app.gateway.harness_review import ReviewHarness
from app.providers.base import ProviderResponse
from app.providers.fake import FakeProvider
from app.vfs.factory import make_local_store

_EMPTY = ProviderResponse(text='{"findings":[]}', model="x")


def _setup_run(store, run_id="r1", languages=None):
    """test_review_harness._setup_run과 동형(테스트 파일 간 import 회피 — 패키지 아님)."""
    languages = languages or ["ko", "en"]
    store.create_run(run_id, languages=languages)
    store.put(f"/{run_id}/brainstorming/plan.md",
              ("---\n"
               f"languages: {languages}\n"
               "factsheet:\n  rate: 5.2\n"
               "disclosures:\n  - 미래 수익 보장 아님\n"
               "---\n# Plan\n"),
              source="marker", mime="text/markdown")
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


def _req():
    return HarnessRequest(run_id="r1", studio="review", user_prompt="검토",
                          provider="fake", is_marker=True)


def _upload_finding():
    return {"location": {"slot": "uploaded", "lang": None},
            "clause": "표시광고법 §3",
            "official_source_url": "https://www.law.go.kr/법령/표시광고의공정화에관한법률",
            "severity": "critical", "evidence": "수익 보장 단정 표현"}


def test_r0_matrix_lists_uploads(tmp_path):
    store = make_local_store(tmp_path)
    _setup_run(store)
    store.put("/r1/review/uploads/poster.png", b"\x89PNG\x00", source="frontend",
              mime="image/png")
    ReviewHarness(vision_provider=FakeProvider()).handle_turn(
        _req(), provider=FakeProvider(), store=store)          # R0
    state = json.loads(store.get("/r1/review/_state.json").content_text)
    assert state["matrix"]["uploads"] == ["poster.png"]


def test_r1_reviews_upload_and_gate_blocks(tmp_path, make_scripted):
    store = make_local_store(tmp_path)
    _setup_run(store)   # languages=["ko","en"], v1.png 존재, _render 없음
    store.put("/r1/review/uploads/violation-poster.png", b"\x89PNG\x00up",
              source="frontend", mime="image/png")
    # 비전 큐: 호출2(v1.png)=empty → 호출4(upload)=critical. (_render 없음 → 호출3 skip)
    vision = make_scripted(review_image_responses=[
        _EMPTY, ProviderResponse(
            text=json.dumps({"findings": [_upload_finding()]}, ensure_ascii=False),
            model="x")])
    # 텍스트 큐: R1/R2/R3의 complete 호출 수에 무관하게 유효 JSON이 나가도록 여유분.
    # '{"findings":[]}'는 R3 reconcile 파서에도 유효(recommendations 부재→[])라 안전.
    text = make_scripted(complete_responses=[_EMPTY] * 6)
    h = ReviewHarness(vision_provider=vision)
    for _ in range(4):                                          # R0→R1→R2→R3
        h.handle_turn(_req(), provider=text, store=store)
    # 호출4 프롬프트 계약(mock 스텁 의존점)
    up_call = vision.calls_review_image[-1]
    assert up_call["prompt"].startswith("[uploaded-audit] file=violation-poster.png")
    # verdict 영속 + 게이트 합류
    verdicts = [json.loads(n.content_text) for n in store.list("/r1/review/legal/")
                if n.path.endswith("verdict.json")]
    up = [v for v in verdicts if v.get("kind") == "uploaded"]
    assert len(up) == 1
    assert up[0]["asset_id"] == "review/uploads/violation-poster.png"
    assert up[0]["location"]["slot"] == "uploaded:violation-poster.png"
    assert store.get_manifest("r1").step_status["review"] == "BLOCKED"
    # R3 리포트 섹션
    report = store.get("/r1/review/report.md").content_text
    assert "## 업로드 소재 심의" in report
    assert "violation-poster.png" in report


def test_no_uploads_regression_single_vision_call(tmp_path, make_scripted):
    """업로드 없으면 비전 호출 수·게이트 산정이 현행과 동일(가산적 계약)."""
    store = make_local_store(tmp_path)
    _setup_run(store)
    vision = make_scripted(review_image_responses=[_EMPTY])
    text = make_scripted(complete_responses=[_EMPTY] * 6)
    h = ReviewHarness(vision_provider=vision)
    for _ in range(4):
        h.handle_turn(_req(), provider=text, store=store)
    assert len(vision.calls_review_image) == 1                  # v1.png 1회뿐
    report = store.get("/r1/review/report.md").content_text
    assert "## 업로드 소재 심의" not in report
