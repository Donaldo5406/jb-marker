"""폐루프 D2 — _remediate_copy가 recommendations.json을 실소비(힌트·고지 언어·출처증빙)."""
import json

from app.gateway.harness import HarnessRequest
from app.gateway.harness_design import _REMEDIATED_DISCLOSURE, DesignHarness
from app.gateway.state import save_state
from app.providers.base import ProviderResponse
from app.providers.fake import FakeProvider
from app.vfs.factory import make_local_store

_COPY = ProviderResponse(text=json.dumps(
    {"copy": {"ko": {"headline": "안전한 카피"}}}, ensure_ascii=False), model="x")

_RECS = [
    {"rec_id": "rec_aaaa1111", "asset_id": "design/final/vi/main.scene", "lang": "vi",
     "target": "text", "instruction": "[missing_disclosure] 예금자보호 고지 누락 — 카피를 교정하세요.",
     "priority": 1, "related_verdict_ids": ["v1"]},
    {"rec_id": "rec_bbbb2222", "asset_id": "design/final/ko/main.scene", "lang": "ko",
     "target": "text", "instruction": "[표시광고법] '업계 최고' 과장 표현 제거",
     "priority": 2, "related_verdict_ids": ["v2"]},
]

_KO_DISC = "가입 전 상품설명서 확인"


def _setup(tmp_path, recs):
    s = make_local_store(tmp_path)
    s.create_run("r1", languages=["ko", "vi"])
    s.put("/r1/brainstorming/plan.md",
          "---\nlanguages: [ko, vi]\nfactsheet:\n  rate: 3.5\n---\n# P",
          source="marker", mime="text/markdown")
    spec = {"slots": [], "aspect": "1:1",
            "copy": {"ko": {"headline": "쉽게", "disclosure": _KO_DISC},
                     "vi": {"headline": "de"}}}
    s.put("/r1/design/rough/layout.spec.json", json.dumps(spec, ensure_ascii=False),
          source="marker", mime="application/json")
    save_state(s, "r1", "design", {"step": "done", "gate": None, "confirmed": {},
                                   "bypass": {}, "languages": ["ko", "vi"]})
    if recs is not None:
        s.put("/r1/review/revise/recommendations.json",
              json.dumps(recs, ensure_ascii=False),
              source="marker", mime="application/json")
    return s


def _req(action=None, prompt=""):
    return HarnessRequest(run_id="r1", studio="design", user_prompt=prompt,
                          provider="anthropic", is_marker=True, action=action)


def _spec(store):
    return json.loads(store.get("/r1/design/rough/layout.spec.json").content_text)


def test_remediate_action_consumes_recs(tmp_path, make_scripted):
    store = _setup(tmp_path, _RECS)
    sp = make_scripted(complete_responses=[_COPY])
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(action="remediate"), provider=sp, store=store)
    # (1) 힌트에 실제 지적이 priority순으로 주입됨 — S2b user 메시지로 전달
    user_msg = sp.calls_complete[0]["messages"][0].content
    assert "rec_aaaa1111" in user_msg and "예금자보호 고지 누락" in user_msg
    assert "업계 최고" in user_msg          # 2순위 지적도 포함
    # (2) 고지 주입 언어가 리뷰 지목 언어(vi)로 좁혀짐 — ko는 기존 고지 보존
    spec = _spec(store)
    assert spec["copy"]["vi"]["disclosure"] == _REMEDIATED_DISCLOSURE["vi"]
    assert spec["copy"]["ko"]["disclosure"] == _KO_DISC
    # (3) 출처증빙 — meta.applied_recs + 응답 텍스트
    applied = res.meta["applied_recs"]
    assert [a["rec_id"] for a in applied] == ["rec_aaaa1111", "rec_bbbb2222"]
    assert res.meta["remediated"] is True
    assert "rec_aaaa1111" in res.text and "2건" in res.text


def test_remediate_without_recs_falls_back(tmp_path, make_scripted):
    """recs 부재 → 현행 동작 보존(고정 힌트·전 언어 고지·기존 문구·applied_recs 없음)."""
    store = _setup(tmp_path, None)
    sp = make_scripted(complete_responses=[_COPY])
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(prompt="리뷰 지적 반영해 수정해줘"), provider=sp, store=store)
    assert "[리뷰 지적을 반영해 카피를 교정하세요]" in sp.calls_complete[0]["messages"][0].content
    spec = _spec(store)
    for lang, disc in _REMEDIATED_DISCLOSURE.items():
        assert spec["copy"].get(lang, {}).get("disclosure") == disc   # 전 언어 폴백
    assert res.meta["remediated"] is True and "applied_recs" not in res.meta


def test_remediate_action_guard_when_not_done(tmp_path, make_scripted):
    store = _setup(tmp_path, _RECS)
    save_state(store, "r1", "design", {"step": "S1", "gate": None, "confirmed": {},
                                       "bypass": {}, "languages": ["ko", "vi"]})
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(action="remediate"), provider=make_scripted(), store=store)
    assert res.meta.get("remediated") is not True
    assert "확정" in res.text                 # 안내 no-op


def test_remediate_action_accepted_over_http(monkeypatch):
    """게이트웨이 Literal에 remediate 개통 — 422가 아니어야 한다(비-done이면 안내 no-op 200)."""
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    from fastapi.testclient import TestClient
    from app.server import create_app
    client = TestClient(create_app())
    rid = client.post("/runs", json={}).json()["run_id"]
    r = client.post("/gateway/run", json={
        "run_id": rid, "studio": "design", "prompt": "",
        "provider": "anthropic", "is_marker": True, "mock": True,
        "action": "remediate"})
    assert r.status_code == 200
    assert "확정" in r.json()["text"]          # done 아님 → 안내 no-op


_MALFORMED_RECS = [
    "not-a-dict-entry",
    {"rec_id": "rec_cccc3333", "asset_id": "design/final/ko/main.scene", "lang": "ko",
     "target": "text", "instruction": "우선순위가 문자열로 오염됨", "priority": "high",
     "related_verdict_ids": ["v3"]},
    {"rec_id": "rec_dddd4444", "asset_id": "design/final/vi/main.scene", "lang": "vi",
     "target": "text", "instruction": "[missing_disclosure] 예금자보호 고지 누락",
     "priority": 1, "related_verdict_ids": ["v4"]},
]


def test_remediate_malformed_recs_no_crash(tmp_path, make_scripted):
    """recs에 비-dict 원소·비-숫자 priority가 섞여도 크래시 없이 dict 항목만 반영."""
    store = _setup(tmp_path, _MALFORMED_RECS)
    sp = make_scripted(complete_responses=[_COPY])
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(action="remediate"), provider=sp, store=store)
    applied = res.meta["applied_recs"]
    # 문자열 원소는 걸러지고(dict만), priority="high"는 99로 폴백해 priority=1보다 뒤로 정렬됨.
    assert [a["rec_id"] for a in applied] == ["rec_dddd4444", "rec_cccc3333"]
    assert res.meta["remediated"] is True


_UPLOAD_REC = {"rec_id": "rec_upload9999", "asset_id": "review/uploads/violation-poster.png",
                "lang": None, "target": "image",
                "instruction": "업로드 포스터에 과장 문구가 있습니다.", "priority": 1,
                "related_verdict_ids": ["vU"]}


def test_remediate_excludes_upload_recs_from_applied(tmp_path, make_scripted):
    """업로드 소재(review/uploads/*) rec은 카피 교정 대상이 아니므로 힌트·applied_recs에서
    제외되고, 일반 rec만 반영된다."""
    store = _setup(tmp_path, [_UPLOAD_REC, _RECS[1]])
    sp = make_scripted(complete_responses=[_COPY])
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(action="remediate"), provider=sp, store=store)
    applied = res.meta["applied_recs"]
    assert [a["rec_id"] for a in applied] == ["rec_bbbb2222"]
    user_msg = sp.calls_complete[0]["messages"][0].content
    assert "rec_upload9999" not in user_msg
    assert "rec_bbbb2222" in user_msg


def test_remediate_upload_only_recs_falls_back(tmp_path, make_scripted):
    """rec이 업로드 소재뿐이면 전량 제외되어 ordered가 비고, recs 부재와 동일한 폴백
    경로(고정 힌트·전 언어 고지·applied_recs 없음)로 처리된다."""
    store = _setup(tmp_path, [_UPLOAD_REC])
    sp = make_scripted(complete_responses=[_COPY])
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(action="remediate"), provider=sp, store=store)
    assert "[리뷰 지적을 반영해 카피를 교정하세요]" in sp.calls_complete[0]["messages"][0].content
    assert "applied_recs" not in res.meta
    assert res.meta["remediated"] is True


def test_remediate_applied_recs_capped_at_six(tmp_path, make_scripted):
    """recs 8건 시드 → applied_recs는 힌트에 실제 주입된 상위 6건과 동일해야 한다."""
    recs8 = [{"rec_id": f"rec_{i:04d}", "lang": "ko", "instruction": f"지적 {i}",
              "priority": i} for i in range(1, 9)]
    store = _setup(tmp_path, recs8)
    sp = make_scripted(complete_responses=[_COPY])
    h = DesignHarness(image_provider=FakeProvider())
    res = h.handle_turn(_req(action="remediate"), provider=sp, store=store)
    applied = res.meta["applied_recs"]
    assert len(applied) == 6
    assert [a["rec_id"] for a in applied] == [f"rec_{i:04d}" for i in range(1, 7)]
    assert "8건 중" in res.text
