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
import os
import re
import time

from ..core.severity import EXAGGERATION_TOKENS
from . import demo_fixtures as F
from .base import Message, Provider, ProviderResponse

logger = logging.getLogger(__name__)


def _latency_base_ms() -> int:
    """DEMO_LATENCY_MS(기본 0=끔) — 데모 체감용 자연 레이턴시 기저값(ms).

    mock 즉답은 라이브 데모에서 인위적으로 보인다(2026-07-04 사용자 지적). 기본 0이라
    테스트·CI는 무영향, 데모 서버만 env로 켠다.
    """
    try:
        return int(os.getenv("DEMO_LATENCY_MS", "0") or "0")
    except ValueError:
        return 0


def _pace(resp: ProviderResponse) -> ProviderResponse:
    """응답 길이에 비례한 지연(기저 + len/4000초, 상한 2.5s) 후 그대로 반환."""
    base_ms = _latency_base_ms()
    if base_ms > 0:
        time.sleep(min(base_ms / 1000 + len(resp.text or "") / 4000, 2.5))
    return resp

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


def controversy_findings(scene_copy: dict) -> list[dict]:
    """scene_copy에서 블랙리스트 신호를 검출 → RC controversy findings(콘텐츠 기반 결정론).

    controversy_rules.evaluate를 재사용해 라이브 LLM 없이 RC를 완주시킨다(mock 결정론).
    하네스 경로 1(결정론 안전망)과 동일 evaluate라 verdict_id가 겹쳐 idempotent(중복 없음).
    clean 카피면 빈 리스트.
    """
    from ..core.controversy_rules import evaluate as _cx_evaluate
    # id를 함께 실어 하네스 경로 2(LLM)가 경로 1(결정론)과 동일 verdict_id로 영속하게 한다
    # → 같은 finding이 두 경로에서 중복 파일이 되지 않고 동일 경로 덮어쓰기(멱등)로 수렴.
    return [{"location": f["location"], "category": f.get("category"),
             "severity": f.get("severity", "warning"),
             "evidence": f.get("evidence", ""),
             "source": f.get("official_source_url", ""),
             "id": f.get("id")}
            for f in _cx_evaluate(scene_copy)]


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
    return json.dumps({"reply": "선택하신 디렉션을 디자인 시스템에 반영해 스펙을 확정했어요.",
                       "document": F.SPEC_MD, "ask": None, "ready": True}, ensure_ascii=False)


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


def _stage_a_brainstorm(messages, medium="image"):
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
    if turns == 3 and medium != "video":
        # AI 제안 턴(spec D4) — 리서치 근거로 디렉션을 권장안으로 제시하고 논의 유도.
        # image 한정: video는 3턴째 spec 불변(D6 영상 무변경)이라 이 블록을 건너뛴다.
        return json.dumps({
            "reply": ("좋아요. 이제 디자인 디렉션이에요 — 리서치에서 봤듯 2030은 금리 수치가 "
                      "또렷하게 보이는 신뢰형 디자인에 반응합니다. 저는 **A안: 신뢰 그린(#00857C) "
                      "베이스 + 골드 포인트, 굵은 디스플레이 헤드라인의 3단 타이포 위계, 라인 "
                      "픽토그램 아이콘**을 권합니다 — 금리 카드와 혜택 칩이 살아나는 조합이에요. "
                      "톤을 더 차분하게 가려면 B안(딥 네이비 미니멀), 더 친근하게는 C안(밝은 "
                      "일러스트)도 가능해요. 어느 방향으로 갈까요?"),
            "document": "",
            "ask": {"trigger": "a", "question": "디자인 디렉션은?",
                    "options": ["A. 신뢰 그린+골드 포인트 (권장)", "B. 딥 네이비 미니멀",
                                "C. 밝은 일러스트 친근형"]},
            "ready": False,
        }, ensure_ascii=False), []
    # 정보 충분 → spec 작성(매체별).
    if medium == "video":
        return json.dumps({"reply": "영상 기획을 정리했어요.", "document": F.VIDEO_SPEC_MD,
                           "ask": None, "ready": True}, ensure_ascii=False), []
    return _spec_json(), []


def _stage_b_brainstorm(system: str, medium="image") -> str:
    """Stage B — 1차 누락 초안 → 보충 후 완성(bypass 패스트패스는 제거됨).

    현재 plan.md(system의 '[현재 plan.md]' 구간)가 비어 있으면 1차(누락) 초안을,
    있으면(보충 단계) 완성 plan을 반환. 누락 초안은 하네스 critic이 'c'(보충)로 유도.
    """
    cur = _section_after(system, "[현재 plan.md]")
    if medium == "video":
        if not cur:
            return json.dumps({"reply": "영상 계획 초안을 잡았어요. 고지·장면 비트를 더 채워야 합니다.",
                               "document": F.VIDEO_PLAN_MD_PARTIAL, "ask": None, "ready": False},
                              ensure_ascii=False)
        return json.dumps({"reply": "빠졌던 고지와 장면 비트를 보강해 영상 계획을 완성했어요.",
                           "document": F.VIDEO_PLAN_MD, "ask": None, "ready": True},
                          ensure_ascii=False)
    # 기존 image 경로(변경 없음)
    if not cur:
        return json.dumps({
            "reply": "계획 초안을 잡았어요. 다만 컴플라이언스 고지와 슬롯 정의를 더 채워야 합니다.",
            "document": F.PLAN_MD_PARTIAL, "ask": None, "ready": False,
        }, ensure_ascii=False)
    return json.dumps({
        "reply": "빠졌던 예금자보호 고지와 레이아웃 슬롯을 보강했습니다. 계획이 완성되었어요.",
        "document": F.PLAN_MD, "ask": None, "ready": True,
    }, ensure_ascii=False)


# S1 티키타카 시그널(spec D3) — 데모 대본의 타이포 디렉션 멘트에 결정론 반응.
# _REMEDIATION_SIGNAL과 동일한 콘텐츠 기반 분기 패턴. 대본 밖 챗은 V1 고정(오발동 가드).
_TIKITAKA_SIGNAL = ("캘리", "골드")


def _layout_json(messages=None) -> str:
    user = _user_text(messages)
    if any(sig in user for sig in _TIKITAKA_SIGNAL):
        return json.dumps({
            "reply": "헤드라인을 붓펜 캘리그래피 질감의 골드 포인트로 키웠어요. "
                     "시안 프리뷰에서 확인해 주세요.",
            "layout_spec": F.LAYOUT_SPEC_V2, "ready": True}, ensure_ascii=False)
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


def _storyboard_json() -> str:
    return json.dumps({"reply": "콘티 완성", "storyboard": F.STORYBOARD_SPEC, "ready": True},
                      ensure_ascii=False)


def _empty_findings() -> str:
    return json.dumps({"findings": []}, ensure_ascii=False)


# S2a bake/edit 프롬프트의 카피 라인 파서 — 두 형식 지원(spec 2026-07-03 D2):
#   baked   : '- headline: 텍스트 (색 #.., 약 NNpx 굵게)'  (steps._bake_prompt / _edit_prompt)
#   directed: 'N. 초대형 헤드라인 (존, 색 #.., 약 NNpx 굵게): "텍스트" — 이 문구만…'
#             (directing._layout_section — DIRECTED_FULLBAKE=1에서 mock 폴백 시 이 형식이 온다)
# 힌트 괄호는 카피가 아니므로 스트립한다(정확 매칭·PIL 베이크 오염 방지).
_COPY_LINE = re.compile(r"^\s*-\s*(headline|body|cta)\s*:\s*(.+?)\s*$", re.MULTILINE)
# 라벨은 directing._ROLE_KR의 복제 — 런타임 import는 providers→gateway 순환 위험이 있어
# 금지하고, 계약 테스트(test_role_label_mapping_matches_directing)로 드리프트를 잠근다.
_ROLE_KR_TO_SLOT = {"초대형 헤드라인": "headline", "본문 서브카피": "body", "CTA 버튼": "cta"}
_DIRECTED_COPY_LINE = re.compile(
    r"^\s*\d+\.\s*(초대형 헤드라인|본문 서브카피|CTA 버튼)(?:\s*\([^)]*\))?\s*:\s*\"(.+?)\"",
    re.MULTILINE)
_HINT_SUFFIX = re.compile(r"\s*\((?:[^()]*(?:색\s*#|px)[^()]*)\)\s*$")
_GOLD_HEX = "#ffd166"   # LAYOUT_SPEC_V2 headline 골드 — 2×2 상태의 골드 축 시그널


def _copy_from_prompt(prompt: str) -> dict:
    """generate_image 프롬프트에서 헤드라인/바디/CTA 카피를 추출(베이크 입력, 두 형식)."""
    out = {m.group(1): _HINT_SUFFIX.sub("", m.group(2)).strip()
           for m in _COPY_LINE.finditer(prompt or "")}
    for m in _DIRECTED_COPY_LINE.finditer(prompt or ""):
        out.setdefault(_ROLE_KR_TO_SLOT[m.group(1)], m.group(2).strip())
    return out


def _headline_gold(prompt: str) -> bool:
    """헤드라인 라인에 골드 힌트(#FFD166)가 있는가 — 2×2 골드 축(라인 한정: 팔레트 오염 가드)."""
    for line in (prompt or "").splitlines():
        if _GOLD_HEX in line.lower() and ("- headline" in line or "초대형 헤드라인" in line):
            return True
    return False


_VIOLATION_TOKENS = ("업계 최고", "4.0%")   # COPY_VIOLATING.ko와 동기(과장·금리 불일치)


def _poster_lang(copy: dict) -> str:
    """카피 언어 감지 — headline이 COPY[lang]과 정확 일치하는 비ko 언어(기본 ko).

    S2a 언어 변형 베이크 프롬프트는 copy[lang]을 글자 그대로 인용(build_director_prompt)
    → 정확 일치로 안전하게 판별된다. 미지 카피는 ko로 두면 상태 매칭이 None → PIL 폴백."""
    hl = (copy or {}).get("headline")
    for lang in ("en", "vi", "zh"):
        if hl == F.COPY[lang]["headline"]:
            return lang
    return "ko"


def _poster_state(copy: dict, prompt: str) -> str | None:
    """파싱된 카피(위반 축) × 헤드라인 골드 힌트(골드 축) → 2×2 fixture 상태(spec D1).

    발표자가 티키타카를 어느 시점에 하든/생략하든 두 축이 독립 검출되어 일관된다.
    비ko 카피는 설계상 clean(COPY_VIOLATING가 COPY 복제) — clean 축으로만 매칭된다."""
    joined = " ".join(str(v) for v in (copy or {}).values())
    gold = _headline_gold(prompt)
    if any(t in joined for t in _VIOLATION_TOKENS):
        return "violating_gold" if gold else "violating"
    if (copy or {}).get("headline") == F.COPY[_poster_lang(copy)]["headline"]:
        return "v2" if gold else "final"
    return None


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


def _controversy_findings_json(messages) -> str:
    """RC: user payload의 scene_copy를 검사해 논란 findings(콘텐츠 기반)."""
    payload = _parse_user(messages)
    return json.dumps({"findings": controversy_findings(payload.get("scene_copy") or {})},
                      ensure_ascii=False)


_UPLOAD_AUDIT_TRIGGERS = ("violation", "논란", "controversy", "tank", "탱크", "위반")

# 욱일기(전범기)·군국주의 도안 포스터 트리거 — RC 논란(other_sensitive) 시연.
# 실제 브랜드가 '일출/햇살(해돋이)' 디자인에 무심코 욱일기 방사선을 넣어 논란 난
# 패턴을 재현한다. 라이브 비전은 파일명과 무관하게 실제 도안을 탐지 — mock은 그
# 경로의 결정론 재현(파일명 트리거). 데모 소재: docs/finals/demo-assets/2026-신년-해돋이-적금.png
_RISING_SUN_TRIGGERS = ("욱일", "전범", "일장", "해돋이", "rising", "sunburst")


def _upload_audit_findings(prompt: str) -> str | None:
    """[uploaded-audit] 프롬프트에 한해 파일명 트리거 기반 결정론 적발(데모).

    실 vision 없이도 mock 시연에서 '업로드 소재 적발'을 재현한다. 트리거 미포함
    파일명은 빈 findings — 거짓 BLOCK 방지(FakeProvider spec §7.3과 동일 원칙).
    비-audit 프롬프트는 None을 반환해 현행 경로(빈 findings)를 그대로 탄다.

    욱일기 트리거는 RC 논란(other_sensitive·category 포함) finding을 반환해 하네스가
    controversy 노드로 라우팅(→ ControversyCard)하게 한다. 일반 트리거는 종전대로
    표시광고법 §3 법률 finding(clause).
    """
    if not prompt.startswith("[uploaded-audit]"):
        return None
    first = prompt.splitlines()[0]
    fname = first.split("file=", 1)[1].strip().lower() if "file=" in first else ""
    if any(t in fname for t in _RISING_SUN_TRIGGERS):
        return json.dumps({"findings": [{
            "location": {"slot": "uploaded", "lang": None},
            "category": "other_sensitive",
            "id": "symbol_rising_sun",
            "severity": "critical",
            "evidence": ("방사형 햇살(16선) 욱일기·전범기 문양 감지 — 일본 군국주의 상징 연상. "
                         "'일출/햇살' 디자인이 의도와 무관하게 반일 정서·불매를 부른 선례 다수."),
        }]}, ensure_ascii=False)
    is_fixture = fname in F.UPLOAD_HIGHLIGHT_BBOX   # 지정 데모 소재(상단 F=demo_fixtures)
    if any(t in fname for t in _UPLOAD_AUDIT_TRIGGERS) or is_fixture:
        location = {"slot": "uploaded", "lang": None}
        if is_fixture:  # 지정 데모 소재 → 구절-tight bbox(하이라이트)
            location["bbox"] = dict(F.UPLOAD_HIGHLIGHT_BBOX[fname])
        return json.dumps({"findings": [{
            "location": location,
            "clause": "표시·광고의 공정화에 관한 법률 §3(부당한 표시·광고 금지)",
            "official_source_url": "https://www.law.go.kr/법령/표시·광고의공정화에관한법률",
            "severity": "critical",
            "evidence": "원금·수익 보장 단정 표현 감지 — '원금 100% 보장'은 오인 유발(데모 결정론 룰)",
        }]}, ensure_ascii=False)
    return _empty_findings()


class DemoProvider(Provider):
    name = "demo"

    def complete(self, messages: list[Message], *, model: str | None = None,
                 system: str | None = None, tools: list[dict] | None = None,
                 meta: dict | None = None, **kwargs) -> ProviderResponse:
        """라우팅(_route) 결과를 자연 레이턴시(_pace, 기본 끔)로 페이싱해 반환."""
        return _pace(self._route(messages, system=system, meta=meta))

    def _route(self, messages: list[Message], *, system: str | None = None,
               meta: dict | None = None) -> ProviderResponse:
        """meta{studio,step} 명시 신호로 단계 라우팅(spec §5.2) — system 문구 비의존.

        system은 단계 감지에 쓰지 않고, stage_b가 '[현재 plan.md]' 컨텍스트 블록의
        **데이터**를 읽는 용도로만 사용(D6 — 하네스가 system 조립을 보존).
        meta 부재/미지 step(compact 포함)은 안전 기본(빈 reply) — Passthrough 경로 보존.
        """
        m = meta or {}
        key = (m.get("studio"), m.get("step"))
        medium = m.get("medium", "image")
        s = system or ""
        if key == ("brainstorming", "stage_a"):   # Stage A — 리서치+멀티턴
            text, citations = _stage_a_brainstorm(messages, medium)
            return ProviderResponse(text=text, model="demo", citations=citations)
        if key == ("brainstorming", "stage_b"):   # Stage B — 1차 누락→보충 완성
            return ProviderResponse(text=_stage_b_brainstorm(s, medium), model="demo")
        if key == ("design", "S1"):               # 러프 레이아웃(티키타카 시그널 분기)
            return ProviderResponse(text=_layout_json(messages), model="demo", raw=None)
        if key == ("design", "S2b"):              # 카피(위반→교정은 콘텐츠 기반)
            return ProviderResponse(text=_copy_json(messages), model="demo", raw=None)
        if key == ("design", "critic"):           # 자기 평가 scores
            return ProviderResponse(text=_critic_json(), model="demo", raw=None)
        if key == ("video", "V1"):                # 콘티
            return ProviderResponse(text=_storyboard_json(), model="demo", raw=None)
        if key == ("video", "V2b"):               # 카피(design과 동일 콘텐츠 분기 재사용)
            return ProviderResponse(text=_copy_json(messages), model="demo", raw=None)
        if key == ("video", "critic"):            # 자기 평가 scores
            return ProviderResponse(text=_critic_json(), model="demo", raw=None)
        if key == ("review", "R1"):               # 법률 — 콘텐츠 기반 적발
            return ProviderResponse(text=_legal_findings_json(messages),
                                    model="demo", raw=None)
        if key == ("review", "R2"):               # 다국어 — 안전망이 고지 누락 처리
            return ProviderResponse(text=_empty_findings(), model="demo", raw=None)
        if key == ("review", "RC"):               # 논란 — 콘텐츠 기반 적발
            return ProviderResponse(text=_controversy_findings_json(messages),
                                    model="demo", raw=None)
        if key == ("review", "R3"):               # 통합 — 콘텐츠 기반 reconcile
            return ProviderResponse(text=_reconcile_json(messages),
                                    model="demo", raw=None)
        logger.debug("demo: unrouted meta %s — 디폴트 응답(빈 reply)", key)
        return ProviderResponse(text=json.dumps({"reply": "", "ready": False},
                                                ensure_ascii=False),
                                model="demo", raw=None)

    def generate_image(self, prompt: str, *, aspect: str = "1:1",
                       image: bytes | None = None,
                       image_size: str | None = None) -> bytes:
        """실모드 S2a와 동등한 결과를 결정적으로 재현(spec 2026-07-03 D1).

        1) 프롬프트에서 카피 파싱(baked/directed 두 형식) → 2×2 상태 매칭 시
           실 Gemini로 사전 생성한 2K 포스터 fixture 반환(프로급 산출물).
        2) 미매칭(미지 카피·비ko 언어 변형)·파일 부재는 현행 PIL 베이크 폴백 — 내일
           라이브 수정으로 카피가 바뀌어도 mock은 반드시 완주한다(회귀 보험).
        """
        base_ms = _latency_base_ms()
        if base_ms > 0:   # 베이크 즉답의 부자연 제거(스펙 D3) — 텍스트보다 긴 고정 지연.
            time.sleep(min(base_ms * 3 / 1000, 3.0))
        copy = _copy_from_prompt(prompt)
        state = _poster_state(copy, prompt)
        if state:
            # 언어 변형(en/vi/zh)은 해당 언어 fixture — 없는 조합은 None → PIL 폴백.
            fixture = F.load_poster_fixture(state, _poster_lang(copy))
            if fixture:
                return fixture
        bg = F.load_poster_bg()
        if copy:
            try:
                from ..core.poster_bake import bake_copy
                return bake_copy(bg, copy, aspect=aspect)
            except Exception:
                logger.exception("demo: 포스터 베이크 실패 — 배경 원본 반환")
        return bg

    def generate_video(self, prompt: str, *, aspect: str = "9:16",
                       duration_sec: int = 15, fps: int = 30) -> bytes:
        # 시연용 결정론 footage — 실 Veo 생성 광고영상(텍스트-free 시네마틱) mp4 바이트.
        # Veo 크레딧 없이도 V2aFootage가 진짜 광고영상 클립을 써 렌더가 실광고물을 만든다.
        # (파일 부재 시 load_demo_video가 still로 graceful 폴백.)
        return F.load_demo_video()

    def review_image(self, image_bytes, prompt, *, mime="image/png") -> ProviderResponse:
        audited = _upload_audit_findings(prompt)
        if audited is not None:
            return ProviderResponse(text=audited, model="demo")
        return ProviderResponse(text=_empty_findings(), model="demo")
