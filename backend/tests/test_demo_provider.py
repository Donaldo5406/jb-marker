import json
import re

from app.providers import demo_fixtures as F

_HANGUL = re.compile(r"[가-힣]")


def test_spec_md_has_required_frontmatter():
    spec = F.SPEC_MD
    for key in ("goal", "target_segments", "channels", "languages", "factsheet", "disclosures"):
        assert f"{key}:" in spec


def test_plan_md_has_all_required_plan_fields():
    from app.gateway.harness_brainstorming import REQUIRED_PLAN_FIELDS, _frontmatter_keys
    keys = _frontmatter_keys(F.PLAN_MD)
    assert REQUIRED_PLAN_FIELDS <= keys, f"missing: {REQUIRED_PLAN_FIELDS - keys}"


def test_layout_spec_shape():
    ls = F.LAYOUT_SPEC
    assert ls["slots"] and ls["visual_concept"] and ls["aspect"]
    assert all({"role", "copy_key"} <= set(s) for s in ls["slots"])


def test_layout_spec_bbox_is_object_form():
    """bbox는 레퍼런스·실 LLM·프론트 assembleScene과 동일한 {x,y,w,h} 객체 형식이어야 한다.
    배열([x,y,w,h])이면 프론트가 s.bbox.x로 읽어 좌표·크기가 전부 undefined가 되어
    텍스트가 원점에 겹치고 배경 이미지 scaleToWidth가 죽는다."""
    for s in F.LAYOUT_SPEC["slots"]:
        assert isinstance(s["bbox"], dict), f"{s['role']} bbox는 dict여야 함(배열 금지)"
        assert {"x", "y", "w", "h"} <= set(s["bbox"]), f"{s['role']} bbox에 x/y/w/h 필요"


def test_vi_zh_copy_has_no_hangul():
    """vi/zh 포스터 한글 토큰 0 (spec T2). 숫자(3.5/12/100)는 유지하되 단위어는 현지화."""
    for lang in ("vi", "zh"):
        for role in ("headline", "body", "cta"):
            val = F.COPY[lang][role]
            assert not _HANGUL.search(val), f"{lang}.{role}에 한글 혼입: {val!r}"


def test_layout_spec_has_disclosure_slot_and_baked_logo_policy():
    """T2(poc_E 개정): 고지 오버레이 슬롯은 유지, 로고는 자산 베이크 → 슬롯 없음 + baked 정책."""
    roles = {s["role"] for s in F.LAYOUT_SPEC["slots"]}
    assert "disclosure" in roles, f"disclosure 슬롯 누락 - {roles}"
    assert "logo" not in roles, "poc_E 경로는 로고 오버레이 OFF(이중 로고 방지)"
    assert F.LAYOUT_SPEC["logo_policy"] == "baked"


def test_copy_numbers_are_grounded_in_factsheet():
    """copy의 모든 수치 토큰이 factsheet corpus에 있어야 grounding 통과."""
    from app.core.grounding import build_corpus, find_ungrounded
    corpus = build_corpus(F.FACTSHEET)
    for lang, fields in F.COPY.items():
        for role in ("headline", "body", "cta"):
            assert not find_ungrounded(fields.get(role, ""), corpus), f"{lang}.{role} ungrounded"


def test_critic_scores_pass():
    from app.gateway.design.scoring import score_layout   # 구 DesignHarness.critic(T1 백로그 ①)
    assert score_layout(F.CRITIC_SCORES)["pass"] is True


def test_placeholder_png_is_valid_png():
    png = F.placeholder_png()
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 100


def _complete(meta: dict, system: str | None = None):
    from app.providers.demo import DemoProvider
    from app.providers.base import Message
    return DemoProvider().complete([Message("user", "x")], model="demo",
                                   system=system, meta=meta)


def _complete_msgs(msgs, meta: dict, system: str | None = None):
    from app.providers.base import Message
    from app.providers.demo import DemoProvider
    return DemoProvider().complete(
        [Message(r, c) for r, c in msgs], model="demo", system=system, meta=meta)


def test_detect_stage_a_turn1_is_interactive_with_research():
    """T5: bypass 없는 1턴 → spec 미작성·질문(a)·리서치 인용 동반."""
    resp = _complete({"studio": "brainstorming", "step": "stage_a"})
    r = json.loads(resp.text)
    assert r["ready"] is False and r["document"] == ""
    assert r["ask"]["trigger"] == "a"
    assert len(resp.citations) >= 1            # 리서치 인용 동반
    assert resp.citations[0]["url"].startswith("http")


def test_detect_stage_a_turn4_returns_full_spec():
    """D4: 충분한 대화(4턴 — 타겟·다국어·디렉션 선택) 후 전체 spec(ready)."""
    msgs = [("user", "정기예금 캠페인"), ("assistant", "타겟은?"),
            ("user", "2030"), ("assistant", "다국어?"), ("user", "영어 포함"),
            ("assistant", "디렉션은?"), ("user", "A안 권장안으로")]
    r = json.loads(_complete_msgs(msgs, {"studio": "brainstorming",
                                         "step": "stage_a"}).text)
    assert r["ready"] is True and "goal:" in r["document"]


def test_detect_stage_b_first_draft_is_partial():
    """T5: 현재 plan 비어있음(1차) → 누락 초안(disclosures/slots 빠짐, ready=false).

    system은 '[현재 plan.md]' 컨텍스트 블록(데이터)만 전달 — 단계 마커 아님(T7)."""
    r = json.loads(_complete({"studio": "brainstorming", "step": "stage_b"},
                             system="페르소나\n\n... [현재 plan.md]\n").text)
    assert r["ready"] is False
    assert "disclosures:" not in r["document"] and "slots:" not in r["document"]
    assert "creative_direction:" in r["document"]


def test_detect_stage_b_after_partial_completes():
    """T5: 현재 plan 존재(보충 단계) → 완성 plan(disclosures/slots 포함, ready)."""
    r = json.loads(_complete(
        {"studio": "brainstorming", "step": "stage_b"},
        system="페르소나\n\n... [현재 plan.md]\n---\ncreative_direction: x\n---\n초안").text)
    assert r["ready"] is True
    assert "disclosures:" in r["document"] and "slots:" in r["document"]


def test_detect_s1_returns_layout_spec():
    r = json.loads(_complete({"studio": "design", "step": "S1"}).text)
    assert "slots" in r["layout_spec"]


def test_detect_s2b_returns_copy_4langs():
    r = json.loads(_complete({"studio": "design", "step": "S2b"}).text)
    assert set(r["copy"]) == {"ko", "en", "vi", "zh"}


def test_detect_s2b_default_returns_violating_copy():
    """T7: 교정 신호 없는 1차 S2b → 위반 카피(유일성·최상급 headline + 절대보장 body, 4개 언어)."""
    r = json.loads(_complete({"studio": "design", "step": "S2b"}).text)
    assert "국내유일" in r["copy"]["ko"]["headline"]       # 유일성·최상급 무근거
    assert "무조건 지급" in r["copy"]["ko"]["body"]        # 절대적 보장 오인
    # poc_E: 비ko도 언어별 위반 카피 스테이징('모든 언어판에서 적발' 서사)
    assert r["copy"]["en"] == F.COPY_VIOLATING["en"]
    assert "No.1" in r["copy"]["en"]["headline"]


def test_detect_s2b_remediation_returns_clean_copy():
    """T7: 사용자가 '보강/교정'을 요청하면(디자인 챗 보조 경로) clean 카피로 재생성."""
    from app.providers.base import Message
    from app.providers.demo import DemoProvider
    r = json.loads(DemoProvider().complete(
        [Message("user", "고지 문구를 보강하고 금리를 교정해줘")],
        model="demo", meta={"studio": "design", "step": "S2b"}).text)
    assert r["copy"] == F.COPY


def test_copy_violating_is_caught_by_legal_findings():
    """T7(poc_E): 위반 카피 → R1 콘텐츠 기반 적발 — 언어당 critical 2(유일성 headline +
    절대보장 body), 4개 언어 전부. clean 카피는 무적발(위반→교정 루프의 양끝)."""
    from app.providers.demo import legal_findings
    fs = legal_findings(F.COPY_VIOLATING)
    crit = [f for f in fs if f["severity"] == "critical"]
    assert len(crit) == 8, [f["evidence"] for f in fs]     # (headline+body) × 4개 언어
    assert {f["location"]["lang"] for f in crit} == {"ko", "en", "vi", "zh"}
    assert legal_findings(F.COPY) == []                     # 교정 후 무적발


def test_detect_critic_returns_passing_scores():
    r = json.loads(_complete({"studio": "design", "step": "critic"}).text)
    assert set(r["scores"]) >= {"hierarchy", "brand"}


def test_review_image_controversy_vision_flags_pinch_on_violating_family(tmp_path, monkeypatch):
    """RC 경로 3(mock): [controversy-vision] + 교정 전 포스터 바이트 → 집게손 warning
    (손 위치 authored bbox 동반). 교정 후(v2)·비RC 프롬프트는 무적발(거짓 논란 방지)."""
    from app.providers.demo import DemoProvider
    for st in ("violating_gold", "v2"):
        (tmp_path / f"poster_{st}.png").write_bytes(F.placeholder_png(64, 80) + st.encode())
    monkeypatch.setattr(F, "_POSTER_DIR", str(tmp_path))
    monkeypatch.setattr(F, "_POSTER_HASHES", None)
    p = DemoProvider()
    viol = F.load_poster_fixture("violating_gold")
    r = json.loads(p.review_image(viol, "[controversy-vision] 논란 판정").text)
    assert len(r["findings"]) == 1
    f = r["findings"][0]
    assert f["severity"] == "warning" and f["category"] == "community_signal"
    assert f["location"]["bbox"] == F.CONTROVERSY_GESTURE_BBOX   # 손 위치 하이라이트
    # 교정 후 포스터 → 무적발(집게손 없는 포즈)
    clean = F.load_poster_fixture("v2")
    assert json.loads(p.review_image(clean, "[controversy-vision] 논란 판정").text)["findings"] == []
    # RC가 아닌 비전 호출(S2a 베이크 검수 등)은 제스처 finding을 내면 안 된다(오탐 가드).
    assert json.loads(p.review_image(viol, "베이크 텍스트 정확성 검수").text)["findings"] == []


def test_detect_review_b_returns_empty_findings():
    r = json.loads(_complete({"studio": "review", "step": "R2"}).text)
    assert r["findings"] == []


def test_demo_generate_image_is_placeholder_png():
    from app.providers.demo import DemoProvider
    png = DemoProvider().generate_image("concept", aspect="1:1")
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 1000  # 1x1보다 큼


def test_demo_review_image_empty_findings():
    from app.providers.demo import DemoProvider
    resp = DemoProvider().review_image(b"x", "prompt")
    assert json.loads(resp.text)["findings"] == []


# --- T3: 콘텐츠 기반 R1 법률 findings / R3 reconcile ---

_VIOLATING = {"ko": {"headline": "업계 최고 연 4.0% 적금",
                     "body": "연 4.0%! 지금 가입하세요", "cta": "가입"}}


def test_demo_legal_findings_detects_violations():
    from app.providers.demo import legal_findings
    fs = legal_findings(_VIOLATING)
    sev = [f["severity"] for f in fs]
    assert sev.count("critical") >= 2          # 과장광고 + 금리 불일치
    assert "warning" in sev                     # 우대조건 단서 누락
    assert fs and all(f["official_source_url"].startswith("https://www.law.go.kr") for f in fs)


def test_demo_legal_findings_clean_fixture_copy_is_empty():
    """데모 기본 카피(F.COPY, 교정본)는 R1 무위반 → 교정 후 PASS 경로 보장."""
    from app.providers.demo import legal_findings
    assert legal_findings(F.COPY) == []


def test_demo_reconcile_summarizes_verdicts_and_resolves_conflict():
    from app.providers.demo import reconcile
    verdicts = [
        {"node": "legal", "verdict_id": "a", "clause": "표시광고법 제3조", "lang": "ko",
         "severity": "critical", "evidence": "과장", "asset_id": "x"},
        {"node": "i18n", "verdict_id": "b", "kind": "missing_disclosure", "lang": "vi",
         "severity": "critical", "evidence": "고지누락", "asset_id": "y"},
    ]
    out = reconcile(verdicts)
    assert len(out["recommendations"]) == 2
    assert out["recommendations"][0]["priority"] == 1   # critical 우선
    assert out["conflicts_resolved"]                     # legal+i18n → 충돌조정 1건


def test_demo_review_personas_route_correctly():
    """검토 3단계 meta 분기 — R1(법률)/R2(다국어)/R3(통합). T7: 페르소나 문구 비의존."""
    from app.providers.demo import DemoProvider
    from app.providers.base import Message

    def call(step, user_obj):
        return json.loads(DemoProvider().complete(
            [Message("user", json.dumps(user_obj, ensure_ascii=False))],
            model="demo", meta={"studio": "review", "step": step}).text)

    r1 = call("R1", {"scene_copy": _VIOLATING})
    assert r1["findings"]                                 # R1 → 위반 적발
    r2 = call("R2", {"ko_copy": {}})
    assert r2["findings"] == []                           # R2 → 안전망 위임(빈손)
    r3 = call("R3", {"verdicts": []})
    assert "recommendations" in r3                        # R3 → reconcile


# ===== 업로드 소재 결정론 적발(mock 데모) =====

def test_review_image_upload_audit_trigger_returns_critical():
    from app.providers.demo import DemoProvider
    p = DemoProvider()
    r = p.review_image(b"\x89PNG", "[uploaded-audit] file=starbucks-tankday-논란.png\n심의하세요")
    findings = json.loads(r.text)["findings"]
    assert len(findings) == 1
    assert findings[0]["severity"] == "critical"
    assert findings[0]["location"]["slot"] == "uploaded"
    assert findings[0]["official_source_url"].startswith("https://www.law.go.kr")


def test_review_image_upload_audit_clean_returns_empty():
    from app.providers.demo import DemoProvider
    p = DemoProvider()
    r = p.review_image(b"\x89PNG", "[uploaded-audit] file=clean-poster.png\n심의하세요")
    assert json.loads(r.text)["findings"] == []


def test_review_image_non_audit_prompt_unchanged():
    from app.providers.demo import DemoProvider
    p = DemoProvider()
    r = p.review_image(b"\x89PNG", "이 이미지는 금융 마케팅 캠페인용 AI 생성 비주얼입니다")
    assert json.loads(r.text)["findings"] == []
