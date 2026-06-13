"""DemoProvider — 시연용 Mock 파이프라인. meta{studio,step} 명시 신호로 단계를 라우팅해 결정적 fixture 반환.

FakeProvider(echo)와 달리 각 하네스가 기대하는 JSON을 돌려줘 BrainStorming→Deploy 전 구간을
끝까지 완주시킨다. 단계 라우팅은 하네스가 주입하는 meta(PromptSpec.meta)에 의존 —
system 프롬프트 문구와 분리되어 프롬프트 수정이 mock을 깨뜨리지 않는다(spec §5.2).

검토(R1 법률 / R3 통합)는 **콘텐츠 기반**: 들어온 scene_copy/verdicts를 검사해 동적으로
findings/recommendations를 생성한다. 위반 카피가 들어오면 위반을 적발하고, 교정된 카피면 사라진다
(요청 간 상태 없는 stateless DemoProvider에서 위반→교정 루프를 성립시키는 핵심, spec §0).
"""
from __future__ import annotations

import json
import logging
import re

from ..core.severity import EXAGGERATION_TOKENS
from . import demo_fixtures as F
from .base import Message, Provider, ProviderResponse

logger = logging.getLogger(__name__)

# JB 정기예금 캠페인 마스터 금리(grounding 진실값). 이와 다른 금리 표기는 허위표시 위반.
_CORRECT_RATE = "3.5%"
# 한국어 과장/단정 표현(severity.EXAGGERATION_TOKENS는 vi/zh만 커버 → ko 보강).
_EXAGGERATION_KO = ("업계 최고", "최고 금리", "최고의", "무조건", "확정 수익", "원금 보장")
_RATE = re.compile(r"\d+(?:\.\d+)?\s*%")
# 우대조건 단서 키워드(언어 무관 부분문자열). 있으면 단서 충족, 없으면 누락(금소법 §22).
_PREFERENTIAL = ("세전", "우대", "pre-tax", "preferential", "trước thuế", "ưu đãi", "税前", "优惠")
# S2b 교정 신호 — 사용자가 위반 카피의 보강/교정을 요청하면 clean 카피로 재생성.
# 일반 디자인 챗에 흔한 광범위 단어(수정·법률·고지)는 false-positive(위반 카피 조기 소거)를
# 유발해 제외 — 교정 의도가 분명한 토큰만 유지(예: "카피 수정해줘"는 더 이상 발동하지 않음).
_REMEDIATION_SIGNAL = ("보강", "교정", "정정", "준법", "fix", "comply")
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


def _count_user_turns(messages) -> int:
    """provider 입력 메시지에서 실제 user 턴 수(압축 요약 헤드 제외)."""
    n = 0
    for m in (messages or []):
        if getattr(m, "role", None) != "user":
            continue
        if (m.content or "").startswith("[이전 대화 요약]"):
            continue   # _window_for_provider가 끼운 요약 헤드는 턴 아님
        n += 1
    return n


def _section_after(system: str, marker: str) -> str:
    """system 프롬프트에서 marker 뒤 구간(예: '[현재 plan.md]' 뒤 현재 plan 내용)."""
    i = (system or "").find(marker)
    return (system[i + len(marker):]).strip() if i >= 0 else ""


def _stage_a_brainstorm(messages):
    """Stage A — 리서치+질문으로 점진 구체화(턴 기반). bypass 패스트패스는 제거됨.

    Returns: (response_text, citations). 1턴에 리서치 인용을 동반(파일 트리에 research 산출).
    """
    turns = _count_user_turns(messages)
    if turns <= 1:
        # 리서치 후 첫 질문(타겟) — 인용 동반.
        return json.dumps({
            "reply": ("정기예금 캠페인이군요. 시장을 빠르게 살펴봤어요 — 2030 세대의 정기예금 "
                      "가입이 늘고 금리 민감도가 높으며 모바일 채널 비중이 큽니다. 먼저 핵심 "
                      "타겟을 누구로 잡을까요?"),
            "document": "",
            "ask": {"trigger": "a", "question": "핵심 타겟 세그먼트는?",
                    "options": ["2030 사회초년생", "3040 자산형성기", "전 연령 일반"]},
            "ready": False,
        }, ensure_ascii=False), F.RESEARCH_CITATIONS
    if turns == 2:
        # 두 번째 질문(다국어 범위) — 리서치 근거 환기.
        return json.dumps({
            "reply": ("좋아요, 2030 사회초년생으로 잡겠습니다. 외국인 고객까지 넓히면 다국어 "
                      "소재가 필요해요. 어느 범위로 제작할까요?"),
            "document": "",
            "ask": {"trigger": "a", "question": "다국어 제작 범위는?",
                    "options": ["국문만", "영어 포함", "영어+베트남어+중국어"]},
            "ready": False,
        }, ensure_ascii=False), []
    # 정보 충분 → 전체 spec 작성(ready).
    return _spec_json(), []


def _stage_b_brainstorm(system: str) -> str:
    """Stage B — 1차 누락 초안 → 보충 후 완성(bypass 패스트패스는 제거됨).

    현재 plan.md(system의 '[현재 plan.md]' 구간)가 비어 있으면 1차(누락) 초안을,
    있으면(보충 단계) 완성 plan을 반환. 누락 초안은 하네스 critic이 'c'(보충)로 유도.
    """
    cur = _section_after(system, "[현재 plan.md]")
    if not cur:
        return json.dumps({
            "reply": "계획 초안을 잡았어요. 다만 컴플라이언스 고지와 슬롯 정의를 더 채워야 합니다.",
            "document": F.PLAN_MD_PARTIAL, "ask": None, "ready": False,
        }, ensure_ascii=False)
    return json.dumps({
        "reply": "빠졌던 예금자보호 고지와 레이아웃 슬롯을 보강했습니다. 계획이 완성되었어요.",
        "document": F.PLAN_MD, "ask": None, "ready": True,
    }, ensure_ascii=False)


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


class DemoProvider(Provider):
    name = "demo"

    def complete(self, messages: list[Message], *, model: str | None = None,
                 system: str | None = None, tools: list[dict] | None = None,
                 meta: dict | None = None, **kwargs) -> ProviderResponse:
        """meta{studio,step} 명시 신호로 단계 라우팅(spec §5.2) — system 문구 비의존.

        system은 단계 감지에 쓰지 않고, stage_b가 '[현재 plan.md]' 컨텍스트 블록의
        **데이터**를 읽는 용도로만 사용(D6 — 하네스가 system 조립을 보존).
        meta 부재/미지 step(compact 포함)은 안전 기본(빈 reply) — Passthrough 경로 보존.
        """
        m = meta or {}
        key = (m.get("studio"), m.get("step"))
        s = system or ""
        if key == ("brainstorming", "stage_a"):   # Stage A — 리서치+멀티턴
            text, citations = _stage_a_brainstorm(messages)
            return ProviderResponse(text=text, model="demo", citations=citations)
        if key == ("brainstorming", "stage_b"):   # Stage B — 1차 누락→보충 완성
            return ProviderResponse(text=_stage_b_brainstorm(s), model="demo")
        if key == ("design", "S1"):               # 러프 레이아웃
            return ProviderResponse(text=_layout_json(), model="demo", raw=None)
        if key == ("design", "S2b"):              # 카피(위반→교정은 콘텐츠 기반)
            return ProviderResponse(text=_copy_json(messages), model="demo", raw=None)
        if key == ("design", "critic"):           # 자기 평가 scores
            return ProviderResponse(text=_critic_json(), model="demo", raw=None)
        if key == ("review", "R1"):               # 법률 — 콘텐츠 기반 적발
            return ProviderResponse(text=_legal_findings_json(messages),
                                    model="demo", raw=None)
        if key == ("review", "R2"):               # 다국어 — 안전망이 고지 누락 처리
            return ProviderResponse(text=_empty_findings(), model="demo", raw=None)
        if key == ("review", "R3"):               # 통합 — 콘텐츠 기반 reconcile
            return ProviderResponse(text=_reconcile_json(messages),
                                    model="demo", raw=None)
        logger.debug("demo: unrouted meta %s — 디폴트 응답(빈 reply)", key)
        return ProviderResponse(text=json.dumps({"reply": "", "ready": False},
                                                ensure_ascii=False),
                                model="demo", raw=None)

    def generate_image(self, prompt: str, *, aspect: str = "1:1") -> bytes:
        # 사용자 제공 배경 비주얼(텍스트-free) 반환 — 단색 placeholder 대체. 부재 시 폴백.
        return F.load_poster_bg()

    def generate_video(self, prompt: str, *, aspect: str = "9:16",
                       duration_sec: int = 15, fps: int = 30) -> bytes:
        # 시연용 결정론 footage — 배경 still 바이트(프론트 VideoEditor가 모션 부여).
        return F.load_poster_bg()

    def review_image(self, image_bytes, prompt, *, mime="image/png") -> ProviderResponse:
        return ProviderResponse(text=_empty_findings(), model="demo")
