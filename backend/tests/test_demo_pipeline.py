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
            "provider": "anthropic", "is_marker": True, "mock": True}
    body.update(kw)
    return client.post("/gateway/run", json=body)


def _seed_brainstorming(client, rid):
    """브레인스토밍 bypass 제거 후 — 멀티턴 대화로 brainstorming을 done까지 구동.
    design/review 셋업용(과거 _run bypass 한 턴 완주를 대체)."""
    def turn(prompt, answer=None):
        body = {"run_id": rid, "studio": "brainstorming", "prompt": prompt,
                "provider": "anthropic", "is_marker": True, "mock": True}
        if answer is not None:
            body["answer"] = answer
        r = client.post("/gateway/run", json=body)
        assert r.status_code == 200, r.text
        return r
    turn("정기예금 캠페인 기획하자")
    turn("2030 사회초년생", answer="2030 사회초년생")
    turn("영어+베트남어+중국어", answer="영어+베트남어+중국어")
    turn("예, plan으로", answer="예, plan으로")     # spec 확정
    turn("보충하기", answer="보충하기")               # plan 누락 보충
    turn("예, 확정", answer="예, 확정")               # plan 확정 → done


def test_brainstorming_demo_produces_spec_and_plan(monkeypatch):
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    _seed_brainstorming(client, rid)
    # 멀티턴 confirm → spec 확정 → plan 보충/확정 → brainstorming done.
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
                "provider": "anthropic", "is_marker": True, "mock": True}
        if answer is not None:
            body["answer"] = answer
        r = client.post("/gateway/run", json=body)
        assert r.status_code == 200
        return r.json()

    # 턴1: 리서치 + 첫 질문(a). spec 아직 미작성.
    r1 = turn("정기예금 캠페인 기획하자")
    assert (r1.get("gate") or {}).get("kind") == "ask"
    assert (r1.get("gate") or {}).get("trigger") == "a"
    assert client.get(f"/vfs/{rid}/brainstorming/spec.md").status_code == 404
    # 리서치 산출물 저장 확인
    src = client.get(f"/vfs/{rid}/brainstorming/assets/research/article/src_0.md")
    assert src.status_code == 200

    # 턴2: 두 번째 질문(a).
    r2 = turn("2030 사회초년생", answer="2030 사회초년생")
    assert (r2.get("gate") or {}).get("trigger") == "a"

    # 턴3: 전체 spec + spec-lock 질문(b).
    r3 = turn("영어+베트남어+중국어", answer="영어+베트남어+중국어")
    assert (r3.get("gate") or {}).get("trigger") == "b"
    spec = client.get(f"/vfs/{rid}/brainstorming/spec.md")
    assert spec.status_code == 200 and "goal:" in spec.json()["content_text"]

    # 턴4: spec 확정 → plan 1차 초안(누락) + 보충 질문(c).
    r4 = turn("예, plan으로", answer="예, plan으로")
    assert (r4.get("gate") or {}).get("trigger") == "c"
    plan_partial = client.get(f"/vfs/{rid}/brainstorming/plan.md").json()["content_text"]
    assert "disclosures:" not in plan_partial   # 1차 누락

    # 턴5: 보충 → 완성 plan + plan-lock 질문(b).
    r5 = turn("보충하기", answer="보충하기")
    assert (r5.get("gate") or {}).get("trigger") == "b"
    plan_full = client.get(f"/vfs/{rid}/brainstorming/plan.md").json()["content_text"]
    assert "creative_direction:" in plan_full and "disclosures:" in plan_full

    # 턴6: plan 확정 → done.
    turn("예, 확정", answer="예, 확정")
    state = client.get(f"/vfs/{rid}/brainstorming/_state.json").json()["content_text"]
    assert '"stage": "done"' in state


def test_design_demo_produces_layout_and_visual(monkeypatch):
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    _seed_brainstorming(client, rid)
    # design: bypass_map으로 전 step OFF → 한 턴 연쇄.
    bm = {s: True for s in ("S1", "S2a", "S2b", "S2c", "S3")}
    r = _run(client, rid, "design", "디자인 시작", action="advance", bypass_map=bm)
    assert r.status_code == 200
    ls = client.get(f"/vfs/{rid}/design/rough/layout.spec.json")
    assert ls.status_code == 200 and "slots" in ls.json()["content_text"]
    png = client.get(f"/vfs/{rid}/design/design-system/components/visual/v1.png")
    assert png.status_code == 200
    # JB 로고 핀: S2c가 기존 logo 슬롯에도 asset_ref를 채우고 로고 PNG를 VFS에 기록해야
    # 어셈블러가 로고를 그린다(Mock 로고 미표시 회귀 가드).
    spec = json.loads(ls.json()["content_text"])
    logo = next((s for s in spec["slots"] if s.get("role") == "logo"), None)
    assert logo and logo.get("asset_ref") == "design-system/components/logo/v1.png", \
        f"logo 슬롯 asset_ref 누락: {logo}"
    logo_png = client.get(f"/vfs/{rid}/design/design-system/components/logo/v1.png")
    assert logo_png.status_code == 200


def test_review_demo_blocks_on_staged_violations(monkeypatch):
    """데모는 의도적으로 위반을 스테이징한다(vi/zh 예금자보호 고지 누락) → 검토가
    이를 잡아 critical → BLOCKED(위반 적발 시연, spec §1③). 검토는 R3까지 완주하고
    보고서·done 상태는 정상 기록된다. 교정 후 PASS 경로는 T7에서 별도 검증."""
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    _seed_brainstorming(client, rid)
    bm = {s: True for s in ("S1", "S2a", "S2b", "S2c", "S3")}
    _run(client, rid, "design", "디자인 시작", action="advance", bypass_map=bm)
    # review는 호출당 한 단계 전진(R0→R1→R2→R3). 프론트 자동 루프와 동일하게 done까지 구동.
    gate: dict = {}
    last_step = None
    for _ in range(6):  # 정상 4단계 + 여유(무한루프 방지)
        r = _run(client, rid, "review", "검토 시작")
        assert r.status_code == 200
        body = r.json()
        g = body.get("gate")
        if g:
            gate = g
        last_step = (body.get("meta") or {}).get("step")
        if last_step == "R3":
            break
    # R3 종단 도달 + 스테이징 위반 적발 → BLOCKED(critical ≥ 1).
    assert last_step == "R3"
    assert gate.get("kind") == "status"   # T1-P2: 응답 top-level GateEnvelope
    assert gate.get("status") == "BLOCKED"
    assert gate.get("critical_count", 0) >= 1
    # 검토 보고서 생성 + state done 확인(BLOCKED여도 검토 단계 자체는 완주).
    report = client.get(f"/vfs/{rid}/review/report.md")
    assert report.status_code == 200
    state = client.get(f"/vfs/{rid}/review/_state.json")
    assert state.status_code == 200 and '"step": "done"' in state.json()["content_text"]


def test_review_r1_flags_ko_exaggeration_and_rate(monkeypatch):
    """R1 법률 검토가 ko 헤드라인 과장광고('업계 최고')·바디 금리 불일치(4.0%≠3.5%)를 적발한다.

    원-레이어에서 헤드라인/바디가 배경 v1.png에 베이크돼 main.scene textbox(=scene_copy)엔
    disclosure만 남아 R1이 무탐이던 회귀 가드 — _collect_scene_copy가 layout.spec 카피를
    베이스로 병합해야 R1이 헤드라인 카피를 본다."""
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    _seed_brainstorming(client, rid)
    bm = {s: True for s in ("S1", "S2a", "S2b", "S2c", "S3")}
    _run(client, rid, "design", "디자인 시작", action="advance", bypass_map=bm)
    for _ in range(6):
        r = _run(client, rid, "review", "검토 시작")
        if (r.json().get("meta") or {}).get("step") == "R3":
            break
    report = client.get(f"/vfs/{rid}/review/report.md").json()["content_text"]
    r1 = report.split("## R1 법률 검토")[1].split("## R2")[0]
    # ko 헤드라인 과장광고(표시광고법 §3) + 바디 금리 불일치(4.0%)가 R1 섹션에 critical로 등장.
    assert "ko" in r1 and "표시" in r1, f"R1이 ko 과장광고를 적발하지 못함:\n{r1}"
    assert ("업계 최고" in r1) or ("4.0%" in r1), f"R1 ko 위반 증거 누락:\n{r1}"


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
        body = r.json()
        g = body.get("gate")
        if g:
            gate = g
        last_step = (body.get("meta") or {}).get("step")
        if last_step == "R3":
            break
    return last_step, gate


def test_review_demo_passes_after_remediation(monkeypatch):
    """위반→교정 루프의 PASS 종단: 사용자가 씬을 교정(위반 카피 제거 + vi/zh 고지 현지화)하면
    재검토가 무위반 → PASS. 결정 A안(FabricEditor 수동 편집)을 main.scene 직접 작성으로 재현한다."""
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    _seed_brainstorming(client, rid)
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


def test_design_chat_remediation_cleans_layout_copy(monkeypatch):
    """리뷰 후 done 상태 디자인 챗의 교정 지시 → S2b 재교정으로 layout.spec copy가 clean.

    결정 B안(디자인 챗 입력으로 교정): 사용자가 '리뷰 결과대로 수정' 류를 입력하면 done
    고정점을 우회해 S2b를 재실행, 위반 카피(업계 최고/4.0%)를 clean 카피로 교체한다.
    프론트는 meta.remediated 신호로 layout.spec을 main.scene으로 재조립(리뷰 재검토 통과)."""
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    _seed_brainstorming(client, rid)
    bm = {s: True for s in ("S1", "S2a", "S2b", "S2c", "S3")}
    _run(client, rid, "design", "디자인 시작", action="advance", bypass_map=bm)

    # 디자인 done + 위반 카피 스테이징 확인
    state = client.get(f"/vfs/{rid}/design/_state.json").json()["content_text"]
    assert '"step": "done"' in state
    before = client.get(f"/vfs/{rid}/design/rough/layout.spec.json").json()["content_text"]
    assert "업계 최고" in before          # COPY_VIOLATING headline(ko)

    # 디자인 챗 자유 교정 지시(action 없음 + 교정 토큰) → remediate 재진입
    r = _run(client, rid, "design", "리뷰 결과대로 카피 수정해줘")
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body.get("meta") or {}).get("remediated") is True
    assert "교정" in (body.get("text") or "")

    after = client.get(f"/vfs/{rid}/design/rough/layout.spec.json").json()["content_text"]
    assert "업계 최고" not in after        # 과장광고 제거
    assert "연 4.0%" not in after          # 금리 불일치 제거
    assert "연 3.5% JB 정기예금" in after   # clean 카피 반영
    assert "예금자보호" in after            # 모든 언어 예금자보호 고지 보강(R2 critical 해소)
    assert "theo luật" in after            # vi 현지화 고지 보강


def test_design_chat_remediation_rebakes_visual(monkeypatch):
    """리뷰 후 디자인 챗 교정 시 v1.png(캔버스 배경)도 clean 카피로 재베이크된다.

    sceneAssembler가 visual_by_lang→background로 v1.png를 그대로 쓰므로(헤드라인 배경 베이크),
    카피·고지만 고치고 비주얼을 두면 캔버스에 위반 텍스트('업계 최고'/4.0%)가 남는다. 회귀 가드."""
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    _seed_brainstorming(client, rid)
    bm = {s: True for s in ("S1", "S2a", "S2b", "S2c", "S3")}
    _run(client, rid, "design", "디자인 시작", action="advance", bypass_map=bm)

    vpath = f"/vfs/{rid}/design/design-system/components/visual/v1.png"
    before = client.get(vpath)
    assert before.status_code == 200
    before_png = before.content   # 이미지는 raw bytes 응답(JSON 아님)

    # 디자인 챗 자유 교정 지시 → 카피·고지 교정 + 비주얼(v1.png) 재베이크
    r = _run(client, rid, "design", "리뷰 결과대로 카피 수정해줘")
    assert r.status_code == 200, r.text
    assert (r.json().get("meta") or {}).get("remediated") is True

    after = client.get(vpath)
    assert after.status_code == 200
    after_png = after.content
    # 위반 카피(업계 최고/4.0%) 베이크 → clean 카피(연 3.5%) 베이크로 비주얼이 달라져야 한다.
    assert after_png != before_png, \
        "remediate 후 v1.png가 재베이크되지 않음 — 캔버스에 위반 비주얼이 잔존한다"


def test_design_chat_nonremediation_keeps_pipeline(monkeypatch):
    """교정 토큰이 없는 일반 디자인 챗(done 상태)은 remediate를 발동하지 않는다(오발동 가드)."""
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    _seed_brainstorming(client, rid)
    bm = {s: True for s in ("S1", "S2a", "S2b", "S2c", "S3")}
    _run(client, rid, "design", "디자인 시작", action="advance", bypass_map=bm)
    r = _run(client, rid, "design", "고마워 잘 됐네")   # 교정 의도 없음
    assert r.status_code == 200
    assert (r.json().get("meta") or {}).get("remediated") is not True
    # 위반 카피는 그대로 유지(조기 소거 없음)
    after = client.get(f"/vfs/{rid}/design/rough/layout.spec.json").json()["content_text"]
    assert "업계 최고" in after


def _assemble_one_layer(client, rid):
    """프론트 sceneAssembler(원-레이어)를 백엔드 테스트에서 재현: 헤드라인은 배경 베이크,
    main.scene에는 disclosure textbox만(copy 필드 없음). + 합성 렌더 시드(vision_skipped 방지)."""
    ls = json.loads(client.get(f"/vfs/{rid}/design/rough/layout.spec.json").json()["content_text"])
    png = base64.b64encode(b"\x89PNG\r\n\x1a\n\x00demo").decode()
    for lang in ("ko", "en", "vi", "zh"):
        disc = (ls.get("copy", {}).get(lang, {}) or {}).get("disclosure", "")
        scene = {"version": "6.0.0", "objects": [
            {"type": "image", "role": "background"},
            {"type": "image", "role": "logo"},
            {"type": "textbox", "role": "disclosure", "text": disc},
        ]}
        client.put(f"/vfs/{rid}/design/final/{lang}/main.scene",
                   json={"content": json.dumps(scene, ensure_ascii=False), "mime": "application/json"})
        client.put(f"/vfs/{rid}/review/_render/{lang}.png",
                   json={"content": png, "content_encoding": "base64", "mime": "image/png"})


def test_design_chat_remediation_then_review_passes(monkeypatch):
    """작업 B 전체 시나리오: 원-레이어 검토 BLOCKED(vi/zh 고지 누락) → 디자인 챗 교정 →
    재조립 → 재검토 PASS. 라이브 동작(헤드라인 배경 베이크)을 그대로 재현해 검증한다."""
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    _seed_brainstorming(client, rid)
    bm = {s: True for s in ("S1", "S2a", "S2b", "S2c", "S3")}
    _run(client, rid, "design", "디자인 시작", action="advance", bypass_map=bm)

    # 1차: 원-레이어 main.scene 조립 → 검토 BLOCKED(예금자보호 고지 누락이 진짜 critical)
    _assemble_one_layer(client, rid)
    last, gate = _drive_review(client, rid)
    assert gate.get("status") == "BLOCKED" and gate.get("critical_count", 0) >= 1

    # 디자인 챗 교정 → layout.spec에 4개 언어 예금자보호 고지 보강
    r = _run(client, rid, "design", "리뷰 결과대로 카피 수정해줘")
    assert (r.json().get("meta") or {}).get("remediated") is True

    # 교정된 layout.spec으로 재조립 → 재검토 PASS
    _assemble_one_layer(client, rid)
    last, gate = _drive_review(client, rid, restart_first=True)
    assert gate.get("status") == "PASS", f"교정 후 PASS 기대, 실제 {gate}"
    assert gate.get("critical_count") == 0
