"""디렉티드 풀베이크 프롬프트 조립기 — 확정 시안 → 아트디렉터 프롬프트 (spec 2026-07-03 §4).

풀베이크 POC(``docs/finals/evidence/fullbake-poc/``, 2026-07-03)의 PROMPT_A를 제품화한
결정론 순수 함수. 전 요소(레이아웃 존·확정 카피·디자인 시스템·금융 수치)를 하나의
아트디렉터 프롬프트로 조립해 ``gemini-3-pro-image`` 원샷 베이크에 넘긴다.

불변 원칙(E 실측 근거):
- **disclosure 전문·조밀 고지 블록은 프롬프트에 넣지 않는다** — 4줄 조밀 잔글씨는 어떤
  풀베이크 모델에서도 깨진다(POC E). 법령 고지는 결정론 오버레이(S2c 슬롯 + sceneAssembler)가
  계속 담당하므로, 여기서는 **하단 스트립을 텍스트 없이 비우라는 safe zone 지시만** 남긴다.
- **로고 렌더 지시 금지** — 로고는 픽셀 정확이 필수라 근사 재그리기가 아닌 결정론 벡터
  슬롯 오버레이(S2c)로 핀한다. 여기서는 **좌상단 모서리를 비우라는 safe zone 지시만** 남긴다.

env flag ``DIRECTED_FULLBAKE`` 뒤 격리 — off(기본)면 S2a는 현행 ``_bake_prompt`` 경로를
바이트 동등하게 유지한다(steps.py 참조).
"""
from __future__ import annotations

import re

from .layout_engine import _dims

_HEX_RE = re.compile(r"#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b")

# 슬롯 role → 프롬프트 서술 라벨. safe zone·데이터 블록으로 별도 처리하는 role은 제외.
_ROLE_KR = {"headline": "초대형 헤드라인", "body": "본문 서브카피", "cta": "CTA 버튼"}

# 카피 서술 순서(POC PROMPT_A의 위→아래 순서 정신 — headline → body → cta).
_COPY_ORDER = ("headline", "body", "cta")


def _num(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def zone_label(bbox: dict, aspect: str) -> str:
    """bbox를 존 언어(상/중/하 · 좌/중/우)로 결정론 번역.

    수직: 슬롯 상단 y를 캔버스 높이 H로 정규화 — y<0.33H=상단, <0.66H=중단, 그 외=하단.
    수평: 슬롯 **중심** x를 폭 W로 정규화 — <0.33W=좌측, <0.66W=중앙, 그 외=우측.
    (brief §3: "y<0.33H=상단…; x 중심으로 좌/중/우 — 결정론 함수로".)
    캔버스 치수는 layout_engine._dims(aspect) 재사용(1080폭 좌표계, 동일 그라운딩).
    """
    W, H = _dims(aspect)
    if not isinstance(bbox, dict):
        return ""
    y = _num(bbox.get("y"))
    cx = _num(bbox.get("x")) + _num(bbox.get("w")) / 2
    fy = (y / H) if H else 0.0
    fx = (cx / W) if W else 0.0
    v = "상단" if fy < 0.33 else ("중단" if fy < 0.66 else "하단")
    h = "좌측" if fx < 0.33 else ("중앙" if fx < 0.66 else "우측")
    return f"{v} {h}"


def _palette_hexes(tokens: dict) -> list:
    """tokens.palette + color_palette에서 hex 컬러만 순서 보존·중복 제거로 추출.

    palette는 리스트, color_palette는 문자열 서술 또는 리스트로 올 수 있다(실 브레인스토밍
    변동성). 두 소스 모두에서 #RRGGBB/#RGB만 뽑아 디자인 시스템 팔레트로 명시한다."""
    out: list = []
    seen: set = set()

    def _add(text: str) -> None:
        for hx in _HEX_RE.findall(text or ""):
            key = hx.lower()
            if key not in seen:
                seen.add(key)
                out.append(hx)

    pal = tokens.get("palette")
    if isinstance(pal, list):
        for c in pal:
            if isinstance(c, str):
                _add(c)
    elif isinstance(pal, str):
        _add(pal)
    cp = tokens.get("color_palette")
    if isinstance(cp, list):
        for c in cp:
            if isinstance(c, str):
                _add(c)
    elif isinstance(cp, str):
        _add(cp)
    return out


def _format_line(aspect: str) -> str:
    """aspect → 포맷 서술(방향 결정론)."""
    W, H = _dims(aspect)
    if H > W:
        shape = "세로형"
    elif W > H:
        shape = "가로형"
    else:
        shape = "정사각형"
    return f"[포맷] {shape} {aspect} 포스터, 고해상도 인쇄용."


def _design_system_section(tokens: dict) -> str:
    """디자인 시스템 섹션 — 팔레트 hex 명시 + 타이포 3단 위계 + 아이콘/사진 그레이드."""
    lines = ["[디자인 시스템 — 전 요소가 이 시스템 하나로 통합될 것]"]
    hexes = _palette_hexes(tokens)
    if hexes:
        lines.append(
            "- 팔레트: " + " · ".join(hexes) +
            ". 모든 포인트 컬러를 이 팔레트로 통일하고, 배경·카드·강조색을 이 안에서만 운용하세요.")
    else:
        lines.append(
            "- 팔레트: 브랜드에 어울리는 절제된 3~4색으로 통일하고, 포인트 컬러를 한 계열로 "
            "묶어 조화시키세요.")
    typo = tokens.get("typography")
    if isinstance(typo, str) and typo.strip():
        lines.append(f"- 타이포 무드: {typo.strip()}")
    lines.append(
        "- 타이포그래피 3단 위계: ① 초대형 헤드라인 = 아주 굵은 모던 한글 산세리프(디스플레이 "
        "웨이트) ② 캘리그래피 악센트 = 붓펜 느낌의 자연스러운 한글 손글씨 한 줄(강조·푸터 전용) "
        "③ 본문 = 깔끔한 중간 굵기 산세리프. 굵기·크기 대비를 분명히 주세요.")
    lines.append(
        "- 아이콘: 동일한 시점·질감·라이팅의 광택 3D 렌더 아이콘 세트 — 네 개가 한 세트처럼 "
        "보이게(소프트 섀도). 밋밋한 클립아트 금지.")
    mood = tokens.get("visual_mood")
    if isinstance(mood, str) and mood.strip():
        lines.append(f"- 사진 그레이드: {mood.strip()} 톤의 프리미엄 은행 광고 화보 마감.")
    else:
        lines.append("- 사진 그레이드: 밝고 청량한 자연광의 프리미엄 은행 광고 화보 톤.")
    return "\n".join(lines)


def _hero_section(spec: dict, tokens: dict) -> str:
    """비주얼/히어로 아트디렉션 — spec.visual_concept + visual_mood 파생."""
    concept = spec.get("visual_concept") or tokens.get("concept") or "금융 브랜드 키비주얼"
    lines = ["[비주얼 / 히어로 — 직접 촬영 디렉팅]", str(concept)]
    lines.append(
        "피사체 피부톤·손가락은 자연스럽게(해부학 왜곡 금지), 헤드라인·카드와 겹치지 않게 "
        "배치하세요.")
    return "\n".join(lines)


def _layout_section(spec: dict, copy: dict, facts: dict, chips: list, aspect: str) -> str:
    """레이아웃·카피 섹션 — 존 언어 번역 + 카피 글자 그대로 인용 + 금리 카드·혜택 행 그라운딩."""
    lines = ["[레이아웃 — 위에서 아래 순서. 텍스트는 아래 지정한 문구를 글자 그대로]"]
    # safe zone을 부정 지시("비워라")가 아니라 그릴 대상(빈 배경·단색 밴드)으로 편성한다 —
    # 라이브 실측(2026-07-03 run a97e4965adc1)에서 절대규칙만으로는 모델이 좌상단에 가짜
    # 로고, 최하단에 깨진 잔글씨 고지를 채웠다. E 스트레스 실측상 "밴드를 그려라"는 지시는
    # 깨끗하게 따르므로 레이아웃 항목으로 격상해 이중 방어한다.
    lines.append(
        "0. 최상단 좌측 모서리: 아무것도 그리지 않은 밝고 단순한 빈 배경 영역 — 공식 로고가 "
        "별도 레이어로 이 자리에 얹히므로 로고·마크·워드마크·글자를 절대 그리지 마세요.")

    # 카피 슬롯의 존·색·크기 힌트 — slots에서 role별로 찾는다(없으면 존 생략).
    slots = spec.get("slots") if isinstance(spec.get("slots"), list) else []
    by_role: dict = {}
    for s in slots:
        if isinstance(s, dict):
            by_role.setdefault(str(s.get("role") or ""), s)

    n = 1
    for role in _COPY_ORDER:
        text = (copy or {}).get(role)
        if not text:
            continue
        slot = by_role.get(role) or (by_role.get("cta_button") if role == "cta" else None)
        zone = zone_label(slot.get("bbox"), aspect) if isinstance(slot, dict) else ""
        hint_bits = []
        if zone:
            hint_bits.append(zone)
        if isinstance(slot, dict):
            if slot.get("color"):
                hint_bits.append(f"색 {slot['color']}")
            if slot.get("font_px"):
                hint_bits.append(f"약 {int(_num(slot['font_px']))}px 굵게")
        hint = f" ({', '.join(hint_bits)})" if hint_bits else ""
        lines.append(f'{n}. {_ROLE_KR[role]}{hint}: "{text}" — 이 문구만, 지정한 그대로.')
        n += 1

    # 금리 하이라이트 카드 — facts 수치만(창작 금지). 최고/기본/우대만 카드로.
    rate_bits = []
    for label in ("최고금리", "기본금리", "우대금리"):
        if facts.get(label):
            rate_bits.append(f"{label} {facts[label]}")
    if rate_bits:
        lines.append(
            f"{n}. 금리 하이라이트 카드(둥근 모서리 화이트 컨테이너·소프트 섀도): 아래 factsheet "
            f"수치만 정확히 렌더하고 핵심 금리 숫자를 가장 크고 굵게 강조하세요 — "
            + " · ".join(rate_bits) + " (이 수치만, 창작·과장 금지).")
        n += 1

    # 혜택 아이콘 칩 행 — _benefit_chips 라벨(그라운딩). 라벨은 글자 그대로.
    if chips:
        lines.append(
            f"{n}. 혜택 아이콘 칩 행(각 칩 = 단순 라인 픽토그램 + 라벨, 가로 균등 정렬): 아래 "
            "라벨을 한 글자도 바꾸지 말고 그대로만 — " + "  |  ".join(str(c) for c in chips))
        n += 1

    # 최하단 밴드도 그릴 대상으로 편성(위 0번 항목과 같은 이중 방어 — 주석 참조).
    lines.append(
        f"{n}. 최하단 가로 스트립: 글자가 단 하나도 없는 어두운 단색 마감 밴드(디자인 요소로만) "
        "— 법령 고지가 별도 레이어로 이 밴드 위에 얹히므로 고지·약관·잔글씨·가짜 텍스트를 "
        "절대 그리지 마세요.")

    return "\n".join(lines)


def _absolute_rules_section() -> str:
    """절대 규칙 — 지정 텍스트만·safe zone·한 장 포스터. disclosure/로고 렌더 지시는 없다."""
    return "\n".join([
        "[절대 규칙]",
        "- 한글 텍스트는 단 한 글자도 틀리면 안 됩니다. 위에 지정한 문구만, 지정한 그대로 "
        "렌더하세요. 임의의 텍스트·숫자·외국어·워터마크·서명·라벨 추가 금지.",
        "- **좌상단 모서리(공식 로고 오버레이 자리)는 밝고 단순하게 비워 두세요** — 로고를 "
        "그리거나 임의의 로고/워드마크를 만들지 마세요(공식 로고는 별도 레이어로 얹습니다).",
        "- **최하단 가로 스트립(법령 고지 오버레이 자리)은 텍스트·요소 없이 단순하게 비워 "
        "두세요** — 조밀한 고지·약관·잔글씨를 절대 굽지 마세요(법령 고지는 별도 레이어로 얹습니다).",
        "- 인물이 든 기기(폰·노트북·태블릿) 화면과 배경 소품·간판은 글자 없이(블랭크) 두세요 "
        "— 가짜 잔글씨 절대 금지.",
        "- \"사진 위에 패널을 얹은\" 느낌 금지 — 처음부터 한 장으로 설계된 포스터처럼 모든 "
        "요소(사진 색감·아이콘 질감·카드·서체)가 서로 어울려야 합니다. 인쇄 검수를 통과한 "
        "최종 납품본 품질로 마감하세요.",
    ])


def build_director_prompt(spec: dict, tokens: dict, facts: dict, chips: list, lang: str) -> str:
    """확정 시안(spec·tokens·facts·chips) → 아트디렉터 원샷 베이크 프롬프트(결정론 순수 함수).

    - spec: ``rough/layout.spec.json`` (slots·copy·visual_concept·aspect).
    - tokens: ``tokens.json`` (palette·color_palette·typography·visual_mood·concept).
    - facts: ``_facts_from_factsheet`` 결과(label→value) — 금리 카드 그라운딩(창작 금지).
    - chips: ``_benefit_chips`` 결과(list[str]) — 혜택 행 라벨 그라운딩.
    - lang: 주 언어 — copy[lang]의 headline/body/cta를 글자 그대로 인용.

    disclosure 전문·로고는 프롬프트에 넣지 않는다(E 실측 — 깨짐/근사). safe zone 지시만 유지.
    """
    spec = spec if isinstance(spec, dict) else {}
    tokens = tokens if isinstance(tokens, dict) else {}
    facts = facts if isinstance(facts, dict) else {}
    chips = chips if isinstance(chips, list) else []
    aspect = str(spec.get("aspect") or tokens.get("aspect") or "1:1")
    copy = (spec.get("copy") or {}).get(lang) or {}
    copy = copy if isinstance(copy, dict) else {}

    sections = [
        "당신은 대한민국 1군 금융광고 스튜디오의 아트디렉터입니다. 아래 명세를 그대로 따른 "
        "프리미엄 은행 포스터 한 장을 완성하세요.",
        _format_line(aspect),
        _design_system_section(tokens),
        _hero_section(spec, tokens),
        _layout_section(spec, copy, facts, chips, aspect),
        _absolute_rules_section(),
    ]
    return "\n\n".join(sections)
