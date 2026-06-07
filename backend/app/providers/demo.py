"""DemoProvider — 시연용 Mock 파이프라인. system 마커로 단계를 감지해 결정적 fixture 반환.

FakeProvider(echo)와 달리 각 하네스가 기대하는 JSON을 돌려줘 BrainStorming→Deploy 전 구간을
끝까지 완주시킨다. 단계 감지는 system 프롬프트의 안정적 마커에 의존(프롬프트 변경 시 통합 테스트가 경보).

검토(R1 법률 / R3 reconciler)는 **콘텐츠 기반**: 들어온 scene_copy/verdicts를 검사해 동적으로
findings/recommendations를 생성한다. 위반 카피가 들어오면 위반을 적발하고, 교정된 카피면 사라진다
(요청 간 상태 없는 stateless DemoProvider에서 위반→교정 루프를 성립시키는 핵심, spec §0).
"""
from __future__ import annotations

import json
import re

from ..core.severity import EXAGGERATION_TOKENS
from . import demo_fixtures as F
from .base import Provider, ProviderResponse

# JB 정기예금 캠페인 마스터 금리(grounding 진실값). 이와 다른 금리 표기는 허위표시 위반.
_CORRECT_RATE = "3.5%"
# 한국어 과장/단정 표현(severity.EXAGGERATION_TOKENS는 vi/zh만 커버 → ko 보강).
_EXAGGERATION_KO = ("업계 최고", "최고 금리", "최고의", "무조건", "확정 수익", "원금 보장")
_RATE = re.compile(r"\d+(?:\.\d+)?\s*%")
# 우대조건 단서 키워드(언어 무관 부분문자열). 있으면 단서 충족, 없으면 누락(금소법 §22).
_PREFERENTIAL = ("세전", "우대", "pre-tax", "preferential", "trước thuế", "ưu đãi", "税前", "优惠")
# S2b 교정 신호 — 사용자가 보강/수정/교정을 요청하면 위반 카피 대신 clean 카피로 재생성.
_REMEDIATION_SIGNAL = ("보강", "수정", "교정", "정정", "고지", "준법", "법률", "fix", "comply")
# 화이트리스트(law.go.kr) 실 deep-link.
_LAW_ADVERTISING = "https://www.law.go.kr/법령/표시ㆍ광고의공정화에관한법률/제3조"
_LAW_CONSUMER = "https://www.law.go.kr/법령/금융소비자보호에관한법률/제22조"


def legal_findings(scene_copy: dict) -> list[dict]:
    """scene_copy(언어별 텍스트)에서 위반 토큰을 검출 → R1 법률 findings(law.go.kr 인용).

    clean 카피면 빈 리스트. 위반 카피에서 #1 과장광고·#2 금리 불일치(critical)·#3 우대단서
    누락(warning)이 점등. #3은 body 슬롯만 검사(헤드라인의 상품명 금리는 제외).
    """
    findings: list[dict] = []
    for lang, copy in (scene_copy or {}).items():
        if not isinstance(copy, dict):
            continue
        for slot in ("headline", "body", "cta"):
            text = str(copy.get(slot, "") or "")
            low = text.lower()
            # #1 과장광고
            if any(tok in text for tok in _EXAGGERATION_KO) or any(
                t.lower() in low for t in EXAGGERATION_TOKENS
            ):
                findings.append({
                    "location": {"slot": slot, "lang": lang},
                    "clause": "표시·광고의 공정화에 관한 법률 제3조",
                    "official_source_url": _LAW_ADVERTISING,
                    "severity": "critical",
                    "evidence": f"객관적 근거 없는 최상급/단정 표현: '{text}'",
                })
            # #2 금리 수치 불일치(마스터 3.5% 외 금리 표기 = 허위표시)
            for tok in _RATE.findall(text):
                norm = tok.replace(" ", "")
                if norm != _CORRECT_RATE:
                    findings.append({
                        "location": {"slot": slot, "lang": lang},
                        "clause": "표시·광고의 공정화에 관한 법률 제3조(허위·과장 광고)",
                        "official_source_url": _LAW_ADVERTISING,
                        "severity": "critical",
                        "evidence": f"표시 금리 '{norm}'가 상품 마스터({_CORRECT_RATE})와 불일치",
                    })
            # #3 우대조건 단서 누락 — body에 금리 표기가 있는데 세전/우대 단서가 없을 때
            if slot == "body" and _RATE.search(text) and not any(
                k.lower() in low for k in _PREFERENTIAL
            ):
                findings.append({
                    "location": {"slot": slot, "lang": lang},
                    "clause": "금융소비자 보호에 관한 법률 제22조",
                    "official_source_url": _LAW_CONSUMER,
                    "severity": "warning",
                    "evidence": "본문 금리 표기에 세전·우대조건 단서 누락",
                })
    return findings


def reconcile(verdicts: list[dict]) -> dict:
    """R1/R2 verdict를 통합 → 우선순위 권장(recommendations) + 충돌조정 요약.

    critical 우선(priority=1), warning 다음(priority=2). 동일 (clause/kind, lang)은 1건으로 묶고
    related_verdict_ids를 모은다. legal·i18n 두 노드가 함께 있으면 conflicts_resolved 1건 기록.
    """
    groups: dict[tuple, dict] = {}
    nodes: set[str] = set()
    for v in verdicts or []:
        node = v.get("node", "")
        nodes.add(node)
        key = (v.get("clause") or v.get("kind") or "", v.get("lang"))
        g = groups.setdefault(key, {
            "asset_id": v.get("asset_id", ""),
            "lang": v.get("lang"),
            "severity": v.get("severity", "warning"),
            "evidence": v.get("evidence", ""),
            "label": key[0],
            "verdict_ids": [],
        })
        g["verdict_ids"].append(v.get("verdict_id", ""))
        if v.get("severity") == "critical":
            g["severity"] = "critical"
    recommendations = []
    for g in groups.values():
        recommendations.append({
            "asset_id": g["asset_id"],
            "lang": g["lang"],
            "target": "text",
            "instruction": f"[{g['label']}] {g['evidence']} — 카피를 교정하세요.",
            "priority": 1 if g["severity"] == "critical" else 2,
            "related_verdict_ids": g["verdict_ids"],
        })
    recommendations.sort(key=lambda r: r["priority"])
    conflicts = []
    if "legal" in nodes and "i18n" in nodes:
        conflicts.append({
            "summary": "법률(R1)·동등성(R2) finding을 통합해 중복 제거·우선순위화했습니다."
        })
    return {"recommendations": recommendations, "conflicts_resolved": conflicts}


def _spec_json() -> str:
    return json.dumps({"reply": "스펙 초안을 정리했어요.", "document": F.SPEC_MD,
                       "ask": None, "ready": True}, ensure_ascii=False)


def _plan_json() -> str:
    return json.dumps({"reply": "구현 계획을 정리했어요.", "document": F.PLAN_MD,
                       "ask": None, "ready": True}, ensure_ascii=False)


def _layout_json() -> str:
    return json.dumps({"reply": "러프 완성", "layout_spec": F.LAYOUT_SPEC, "ready": True},
                      ensure_ascii=False)


def _copy_json(messages=None) -> str:
    """S2b 카피. 기본은 위반 카피(시연용 적발 대상), 교정 신호가 있으면 clean 카피.

    stateless DemoProvider에서 위반→교정 루프를 성립시키는 콘텐츠 기반 분기(spec §0).
    주 교정 경로는 FabricEditor 씬 수동 편집이며, 이 분기는 디자인 챗 재생성(보강 지시)용 보조 경로.
    """
    user = _user_text(messages).lower()
    copy = F.COPY if any(sig in user for sig in _REMEDIATION_SIGNAL) else F.COPY_VIOLATING
    return json.dumps({"copy": copy}, ensure_ascii=False)


def _critic_json() -> str:
    return json.dumps({"scores": F.CRITIC_SCORES}, ensure_ascii=False)


def _empty_findings() -> str:
    return json.dumps({"findings": []}, ensure_ascii=False)


def _user_text(messages) -> str:
    """messages에서 마지막 user 콘텐츠 추출(콘텐츠 기반 탐지 입력)."""
    for m in reversed(list(messages or [])):
        if getattr(m, "role", None) == "user":
            return m.content or ""
    return ""


def _parse_user(messages) -> dict:
    try:
        return json.loads(_user_text(messages))
    except Exception:
        return {}


def _legal_findings_json(messages) -> str:
    """R1: user payload의 scene_copy를 검사해 위반 findings(콘텐츠 기반)."""
    payload = _parse_user(messages)
    return json.dumps({"findings": legal_findings(payload.get("scene_copy") or {})},
                      ensure_ascii=False)


def _reconcile_json(messages) -> str:
    """R3: user payload의 verdicts를 통합해 recommendations(콘텐츠 기반)."""
    payload = _parse_user(messages)
    return json.dumps(reconcile(payload.get("verdicts") or []), ensure_ascii=False)


def _detect(system: str, messages=None) -> str:
    """system 마커로 단계 판별 → 해당 fixture/콘텐츠. 미매칭은 안전 기본."""
    s = system or ""
    if "[Stage A]" in s:
        return _spec_json()
    if "[Stage B]" in s:
        return _plan_json()
    if "[S1 Rough]" in s:
        return _layout_json()
    if "[S2b" in s:
        return _copy_json(messages)
    if "[자기-크리틱]" in s:
        return _critic_json()
    if "reconciler" in s:                       # Review R3 (PERSONA_C)
        return _reconcile_json(messages)
    if "동등성" in s:                            # Review R2 (PERSONA_B) — 안전망이 고지 누락 처리
        return _empty_findings()
    if "표시광고법" in s or "법률 검토관" in s:   # Review R1 (PERSONA_A 법률) — 콘텐츠 기반
        return _legal_findings_json(messages)
    if "검토관" in s or "법령" in s or "법률" in s:  # 기타 검토 페르소나 폴백
        return _empty_findings()
    return json.dumps({"reply": "", "ready": False}, ensure_ascii=False)


class DemoProvider(Provider):
    name = "demo"

    def complete(self, messages, *, model, system=None, tools=None, **kwargs) -> ProviderResponse:
        return ProviderResponse(text=_detect(system or "", messages), model="demo", raw=None)

    def generate_image(self, prompt: str, *, aspect: str = "1:1") -> bytes:
        # 사용자 제공 배경 비주얼(텍스트-free) 반환 — 단색 placeholder 대체. 부재 시 폴백.
        return F.load_poster_bg()

    def review_image(self, image_bytes, prompt, *, mime="image/png") -> ProviderResponse:
        return ProviderResponse(text=_empty_findings(), model="demo")
