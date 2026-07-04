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
    # 비전 큐: 호출2(v1.png)=empty → 호출4(upload)=critical → RC v1.png=empty. (_render 없음 → 호출3 skip)
    vision = make_scripted(review_image_responses=[
        _EMPTY, ProviderResponse(
            text=json.dumps({"findings": [_upload_finding()]}, ensure_ascii=False),
            model="x"), _EMPTY])   # 끝 _EMPTY = RC 단계 v1.png 비전
    # 텍스트 큐: R1/R2/RC/R3의 complete 호출 수에 무관하게 유효 JSON이 나가도록 여유분.
    # '{"findings":[]}'는 R3 reconcile 파서에도 유효(recommendations 부재→[])라 안전.
    text = make_scripted(complete_responses=[_EMPTY] * 6)
    h = ReviewHarness(vision_provider=vision)
    for _ in range(5):                                          # R0→R1→R2→RC→R3
        h.handle_turn(_req(), provider=text, store=store)
    # 호출4 프롬프트 계약(mock 스텁 의존점) — RC 비전이 뒤에 붙으므로 upload-audit 호출을 특정
    up_call = next(c for c in vision.calls_review_image
                   if c["prompt"].startswith("[uploaded-audit]"))
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
    """업로드 없으면 업로드 심의(upload-audit) 비전 호출·리포트 섹션이 없다(가산적 계약).

    RC 단계가 v1.png 비전을 1회 더 호출하므로 총 비전 호출 수 대신 'upload-audit 호출 부재'로
    무업로드 회귀를 검증한다(파이프라인 단계 변화에 견고)."""
    store = make_local_store(tmp_path)
    _setup_run(store)
    vision = make_scripted(review_image_responses=[_EMPTY, _EMPTY])
    text = make_scripted(complete_responses=[_EMPTY] * 6)
    h = ReviewHarness(vision_provider=vision)
    for _ in range(5):                                          # R0→R1→R2→RC→R3
        h.handle_turn(_req(), provider=text, store=store)
    assert not any(c["prompt"].startswith("[uploaded-audit]")
                   for c in vision.calls_review_image)          # 업로드 심의 호출 없음
    report = store.get("/r1/review/report.md").content_text
    assert "## 업로드 소재 심의" not in report


def test_upload_audit_rising_sun_returns_controversy_finding():
    """욱일기 트리거 파일명 → other_sensitive·critical 논란 finding(카테고리 포함, clause 없음)."""
    from app.providers.demo import _upload_audit_findings

    out = _upload_audit_findings("[uploaded-audit] file=2026-신년-해돋이-적금.png\n심의")
    f = json.loads(out)["findings"][0]
    assert f["category"] == "other_sensitive"     # → controversy 노드 라우팅 신호
    assert f["id"] == "symbol_rising_sun"          # verdict_id 유일성(identity)
    assert f["severity"] == "critical"
    assert "욱일기" in f["evidence"]
    assert "clause" not in f                        # 법률 아님 — 법령 화이트리스트 비대상


def test_rising_sun_upload_routes_to_controversy_and_blocks(tmp_path, make_scripted):
    """욱일기 포스터 업로드 → controversy 노드 영속 + 게이트 BLOCKED + 리포트 RC 섹션.

    DemoProvider를 비전으로 써 '해돋이' 파일명 트리거로 mock 결정론 적발을 재현한다
    (라이브 비전은 파일명 무관 실도안 탐지). 법률 화이트리스트에 걸려 드롭되지 않고
    controversy로 라우팅되는지가 핵심."""
    from app.providers.demo import DemoProvider

    store = make_local_store(tmp_path)
    _setup_run(store)
    store.put("/r1/review/uploads/2026-신년-해돋이-적금.png", b"\x89PNG\x00sun",
              source="frontend", mime="image/png")
    text = make_scripted(complete_responses=[_EMPTY] * 6)
    h = ReviewHarness(vision_provider=DemoProvider())
    for _ in range(5):                                          # R0→R1→R2→RC→R3
        h.handle_turn(_req(), provider=text, store=store)
    # controversy 노드에 업로드 욱일기 verdict(법률 화이트리스트에 드롭 안 됨)
    cx = [json.loads(n.content_text) for n in store.list("/r1/review/controversy/")
          if n.path.endswith("verdict.json")]
    rising = [v for v in cx if v.get("kind") == "other_sensitive"
              and str(v.get("location", {}).get("slot", "")).startswith("uploaded")]
    assert len(rising) == 1
    assert rising[0]["severity"] == "critical"
    assert rising[0]["asset_id"] == "review/uploads/2026-신년-해돋이-적금.png"
    assert "clause" not in rising[0]                            # 논란 봉투(법률 아님)
    # critical → 게이트 BLOCKED + 리포트 RC 섹션에 근거 표면화
    assert store.get_manifest("r1").step_status["review"] == "BLOCKED"
    report = store.get("/r1/review/report.md").content_text
    assert "## RC 논란 검토" in report
    assert "욱일기" in report
