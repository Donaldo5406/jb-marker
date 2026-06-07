"""demo(mock)로 BrainStorming→Design→Review 전 구간 완주 — 끝까지 도는 mock 검증."""
import base64
import json

from fastapi.testclient import TestClient


def _client(monkeypatch):
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    from app.server import create_app
    return TestClient(create_app())


def _run(client, rid, studio, prompt, **kw):
    body = {"run_id": rid, "studio": studio, "prompt": prompt,
            "provider": "anthropic", "is_marker": True, "mock": True, "bypass": True}
    body.update(kw)
    return client.post("/gateway/run", json=body)


def test_brainstorming_demo_produces_spec_and_plan(monkeypatch):
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    r = _run(client, rid, "brainstorming", "정기예금 캠페인")
    assert r.status_code == 200
    # bypass → Stage A ready → Stage B 자동 진입 → plan 생성, brainstorming done.
    spec = client.get(f"/vfs/{rid}/brainstorming/spec.md")
    plan = client.get(f"/vfs/{rid}/brainstorming/plan.md")
    assert spec.status_code == 200 and "goal:" in spec.json()["content_text"]
    assert plan.status_code == 200 and "creative_direction:" in plan.json()["content_text"]


def test_brainstorming_demo_interactive_research_to_plan(monkeypatch):
    """T5: bypass 없는 멀티턴 — 리서치+질문(a) → spec(b) → plan 1차 누락(c) →
    보충 후 완성(b) → 확정(done). 인터랙티브 기획 흐름 전 구간 시연."""
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]

    def turn(prompt, answer=None):
        body = {"run_id": rid, "studio": "brainstorming", "prompt": prompt,
                "provider": "anthropic", "is_marker": True, "mock": True, "bypass": False}
        if answer is not None:
            body["answer"] = answer
        r = client.post("/gateway/run", json=body)
        assert r.status_code == 200
        return r.json()

    # 턴1: 리서치 + 첫 질문(a). spec 아직 미작성.
    r1 = turn("정기예금 캠페인 기획하자")
    assert (r1.get("ask") or {}).get("trigger") == "a"
    assert client.get(f"/vfs/{rid}/brainstorming/spec.md").status_code == 404
    # 리서치 산출물 저장 확인
    src = client.get(f"/vfs/{rid}/brainstorming/assets/research/article/src_0.md")
    assert src.status_code == 200

    # 턴2: 두 번째 질문(a).
    r2 = turn("2030 사회초년생", answer="2030 사회초년생")
    assert (r2.get("ask") or {}).get("trigger") == "a"

    # 턴3: 전체 spec + spec-lock 질문(b).
    r3 = turn("영어+베트남어+중국어", answer="영어+베트남어+중국어")
    assert (r3.get("ask") or {}).get("trigger") == "b"
    spec = client.get(f"/vfs/{rid}/brainstorming/spec.md")
    assert spec.status_code == 200 and "goal:" in spec.json()["content_text"]

    # 턴4: spec 확정 → plan 1차 초안(누락) + 보충 질문(c).
    r4 = turn("예, plan으로", answer="예, plan으로")
    assert (r4.get("ask") or {}).get("trigger") == "c"
    plan_partial = client.get(f"/vfs/{rid}/brainstorming/plan.md").json()["content_text"]
    assert "disclosures:" not in plan_partial   # 1차 누락

    # 턴5: 보충 → 완성 plan + plan-lock 질문(b).
    r5 = turn("보충하기", answer="보충하기")
    assert (r5.get("ask") or {}).get("trigger") == "b"
    plan_full = client.get(f"/vfs/{rid}/brainstorming/plan.md").json()["content_text"]
    assert "creative_direction:" in plan_full and "disclosures:" in plan_full

    # 턴6: plan 확정 → done.
    turn("예, 확정", answer="예, 확정")
    state = client.get(f"/vfs/{rid}/brainstorming/_state.json").json()["content_text"]
    assert '"stage": "done"' in state


def test_design_demo_produces_layout_and_visual(monkeypatch):
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    _run(client, rid, "brainstorming", "정기예금 캠페인")
    # design: bypass_map으로 전 step OFF → 한 턴 연쇄.
    bm = {s: True for s in ("S1", "S2a", "S2b", "S2c", "S3")}
    r = _run(client, rid, "design", "디자인 시작", action="advance", bypass_map=bm)
    assert r.status_code == 200
    ls = client.get(f"/vfs/{rid}/design/rough/layout.spec.json")
    assert ls.status_code == 200 and "slots" in ls.json()["content_text"]
    png = client.get(f"/vfs/{rid}/design/design-system/components/visual/v1.png")
    assert png.status_code == 200


def test_review_demo_blocks_on_staged_violations(monkeypatch):
    """데모는 의도적으로 위반을 스테이징한다(vi/zh 예금자보호 고지 누락) → 검토가
    이를 잡아 critical → BLOCKED(위반 적발 시연, spec §1③). 검토는 R3까지 완주하고
    보고서·done 상태는 정상 기록된다. 교정 후 PASS 경로는 T7에서 별도 검증."""
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    _run(client, rid, "brainstorming", "정기예금 캠페인")
    bm = {s: True for s in ("S1", "S2a", "S2b", "S2c", "S3")}
    _run(client, rid, "design", "디자인 시작", action="advance", bypass_map=bm)
    # review는 호출당 한 단계 전진(R0→R1→R2→R3). 프론트 자동 루프와 동일하게 done까지 구동.
    gate: dict = {}
    last_step = None
    for _ in range(6):  # 정상 4단계 + 여유(무한루프 방지)
        r = _run(client, rid, "review", "검토 시작")
        assert r.status_code == 200
        meta = r.json().get("meta") or {}
        if meta.get("gate"):
            gate = meta["gate"]
        last_step = meta.get("step")
        if last_step == "R3":
            break
    # R3 종단 도달 + 스테이징 위반 적발 → BLOCKED(critical ≥ 1).
    assert last_step == "R3"
    assert gate.get("status") == "BLOCKED"
    assert gate.get("critical_count", 0) >= 1
    # 검토 보고서 생성 + state done 확인(BLOCKED여도 검토 단계 자체는 완주).
    report = client.get(f"/vfs/{rid}/review/report.md")
    assert report.status_code == 200
    state = client.get(f"/vfs/{rid}/review/_state.json")
    assert state.status_code == 200 and '"step": "done"' in state.json()["content_text"]


# 교정된 4언어 카피 — 위반 토큰 제거 + vi/zh 예금자보호 고지 현지화 키워드 포함.
# (FabricEditor 씬 수동 편집 = 결정 A안의 결과물을 백엔드 테스트에서 재현)
_REMEDIATED = {
    "ko": {"headline": "연 3.5% JB 정기예금", "body": "12개월 만기, 100만원부터 시작하세요.",
           "cta": "지금 가입하기", "disclosure": "예금자보호법에 따라 5천만원까지 보호"},
    "en": {"headline": "JB Term Deposit at 3.5%", "body": "12-month term. Open online in minutes.",
           "cta": "Open now", "disclosure": "Protected up to KRW 50M under the Depositor Protection Act."},
    "vi": {"headline": "JB Tiết kiệm 3.5%", "body": "Kỳ hạn 12 tháng, từ 100 vạn won.",
           "cta": "Mở ngay", "disclosure": "Được bảo hiểm tiền gửi tới 50 triệu KRW theo luật."},
    "zh": {"headline": "JB定期存款 3.5%", "body": "12个月期限，100万韩元起。",
           "cta": "立即开户", "disclosure": "根据存款保护法，最高保护5000万韩元。"},
}


def _drive_review(client, rid, restart_first=False):
    """review를 R3 종단까지 구동하고 (last_step, gate) 반환.

    restart_first=True면 첫 호출에 restart(done→R0 멱등 재구축, 재검토용)."""
    gate: dict = {}
    last_step = None
    for i in range(6):
        kw = {"action": "restart"} if (restart_first and i == 0) else {}
        r = _run(client, rid, "review", "검토 시작", **kw)
        assert r.status_code == 200
        meta = r.json().get("meta") or {}
        if meta.get("gate"):
            gate = meta["gate"]
        last_step = meta.get("step")
        if last_step == "R3":
            break
    return last_step, gate


def test_review_demo_passes_after_remediation(monkeypatch):
    """위반→교정 루프의 PASS 종단: 사용자가 씬을 교정(위반 카피 제거 + vi/zh 고지 현지화)하면
    재검토가 무위반 → PASS. 결정 A안(FabricEditor 수동 편집)을 main.scene 직접 작성으로 재현한다."""
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    _run(client, rid, "brainstorming", "정기예금 캠페인")
    bm = {s: True for s in ("S1", "S2a", "S2b", "S2c", "S3")}
    _run(client, rid, "design", "디자인 시작", action="advance", bypass_map=bm)

    # 1차 검토 → 스테이징 위반으로 BLOCKED 확인
    last_step, gate = _drive_review(client, rid)
    assert last_step == "R3" and gate.get("status") == "BLOCKED"

    # 교정: 4언어 main.scene을 clean 카피로 덮어쓴다(=씬 수동 편집). scene_copy가
    # layout.spec.json 폴백보다 우선되어 검토가 교정본을 본다.
    png_b64 = base64.b64encode(b"\x89PNG\r\n\x1a\n\x00demo").decode()
    for lang, copy in _REMEDIATED.items():
        client.put(f"/vfs/{rid}/design/final/{lang}/main.scene",
                   json={"content": json.dumps({"copy": {lang: copy}}, ensure_ascii=False),
                         "mime": "application/json"})
        # 합성 렌더 시드 — 없으면 vision_skipped가 PASS를 WARN으로 강등.
        client.put(f"/vfs/{rid}/review/_render/{lang}.png",
                   json={"content": png_b64, "content_encoding": "base64", "mime": "image/png"})

    # 재검토(restart=R0부터 멱등 재구축) → 무위반 PASS
    last_step, gate = _drive_review(client, rid, restart_first=True)
    assert last_step == "R3"
    assert gate.get("status") == "PASS", f"교정 후 PASS 기대, 실제 {gate}"
    assert gate.get("critical_count") == 0
