"""Design 프롬프트 상수 — PERSONA·단계 지시문 (구 harness_design.py:41-79 이동, T3 P2)."""

PERSONA = (
    "당신은 금융 마케팅 시니어 아트디렉터입니다. 시각 위계·그리드·여백·CTA 배치·"
    "브랜드 일관성·컴플라이언스 톤에 능하며, 인물·배경·구도·조명·색온도를 아우르는 "
    "키비주얼과 헤드라인·CTA 타이포그래피를 한 화면에 통합 디자인합니다. "
    "단, 공식 로고와 법령 고지가 놓일 영역(좌상단·하단)은 단순·저대비로 비워 둡니다. "
    "레이아웃은 구조화 JSON으로만 출력합니다."
)

# [S1 Rough] 지시·JSON 예시 — PromptSpec.constraints 단일 원소(문자열은 인라인 시절과 동일, D6).
S1_INSTR = (
    "\n\n[S1 Rough] 아래 레퍼런스 레이아웃을 참고해 layout_spec(JSON)을 출력하세요. "
    "slots에는 반드시 headline·body·cta·disclosure 4개 역할을 모두 포함하고, "
    "각 슬롯은 role·bbox{x,y,w,h}·z·copy_key를 갖습니다. 텍스트는 copy[lang][key]에 둡니다. "
    "headline·cta·body의 font_px(정수)·color(#RRGGBB)는 비주얼에 구울 타이포 가이드입니다. "
    "색은 **위계 있게** 배정하세요 — 헤드라인·CTA는 tokens.palette의 브랜드 포인트 컬러로 "
    "강한 대비, 바디는 가독 중립색. 전부 한 가지 어두운 색으로 두면 단조로우니 피하세요. "
    "최상위에 bg_color(#RRGGBB)와 visual_concept(문자열)을 **반드시** 포함하세요. "
    "visual_concept은 **헤드라인·CTA 텍스트까지 통합된 풀 포스터**의 상세 아트디렉션입니다: "
    "피사체(인물 포함 시 포즈·표정·시선·연령대·복장)·배경·구도·조명·색감·분위기와 "
    "헤드라인/CTA가 어떻게 디자인되는지 구체 서술하세요. "
    "품질 기준은 **실제 금융 브랜드 광고 수준**입니다 — 전문 광고 사진급 자연광·"
    "시네마틱 라이팅과 얕은 심도, 편집 디자인다운 그리드·여백·타이포 위계, 고급스럽고 "
    "신뢰감 있는 브랜드 색감을 명시하세요(스톡·클립아트·평면적 느낌 지양). "
    "단 **좌상단 모서리(공식 로고)와 하단 스트립(법령 고지)은 텍스트·요소 없이 "
    "단순·저대비로 비워 둘 것**(오버레이 safe zone)을 명시하세요. "
    "tokens의 color_palette·typography·concept(있으면)를 색·폰트·톤·visual_concept에 "
    "반영하고, aspect는 tokens.aspect를 따르세요. 정확한 출력 형식 예시:\n"
    '{"reply":"...","ready":true,"layout_spec":{"aspect":"4:5","bg_color":"#F2EFE9",'
    '"visual_concept":"밝은 채광의 카페 창가, 20대 청년이 통장을 들고 환하게 미소, 상반신. '
    '상단에 굵은 헤드라인 \'청년 적금으로 미래를 더 크게\', 하단에 둥근 CTA 버튼 \'지금 신청\'을 '
    '따뜻한 색감으로 통합 디자인. 좌상단 모서리와 하단 스트립은 비워 둠(로고·고지 오버레이용)",'
    '"slots":['
    '{"role":"headline","bbox":{"x":80,"y":120,"w":920,"h":180},"z":3,"copy_key":"headline","font_px":96,"color":"#0B1324"},'
    '{"role":"body","bbox":{"x":80,"y":340,"w":900,"h":120},"z":2,"copy_key":"body","font_px":40,"color":"#1A2332"},'
    '{"role":"cta","bbox":{"x":80,"y":980,"w":520,"h":96},"z":3,"copy_key":"cta","font_px":44,"color":"#FFFFFF"},'
    '{"role":"disclosure","bbox":{"x":80,"y":1180,"w":920,"h":120},"z":1,"copy_key":"disclosure","font_px":30,"color":"#3A3A3A"}'
    '],"copy":{"ko":{"headline":"...","body":"...","cta":"...","disclosure":"..."}}}}'
    "\nJSON 한 개만 출력(코드펜스·주석 금지)."
)

# [S2b] 지시·JSON 형식 — 혼합 블록이라 constraints 1원소(문자열은 인라인 시절과 동일, D6).
S2B_INSTR = (
    "\n\n[S2b 카피·타이포] 헤드라인/바디/CTA를 언어별로 확정하세요. "
    'factsheet 외 수치 금지. JSON: {"copy":{lang:{headline,body,cta}}}'
)

# [자기-크리틱] 지시 — 전체 정적이라 constraints 1원소(문자열은 인라인 시절과 동일, D6).
CRITIC_INSTR = (
    "\n\n[자기-크리틱] 아래 레이아웃을 hierarchy/grid/whitespace/cta/"
    "compliance/copy_visual/brand 7항목으로 1~5 채점하세요. "
    'JSON 한 개만: {"scores":{"hierarchy":n,...}}'
)

# [S2a 비전 게이트] 베이크된 풀 포스터의 텍스트·로고 정확성 검증(누출탐지 반전).
_S2A_VISION_BASE = (
    "이 이미지는 금융 마케팅 포스터의 AI 생성 결과입니다. 헤드라인·CTA 텍스트가 "
    "비주얼에 통합 렌더돼 있습니다. 다음을 점검해 결함만 보고하세요: "
    "① 렌더된 텍스트가 아래 '기대 카피'와 **정확히 일치**하는가 — 오타·누락·글자 깨짐·"
    "환각 문구(불일치=critical). "
    "② 인물이 있다면 손가락·손·얼굴 등 해부학적 왜곡(왜곡=critical). "
    "③ 좌상단(로고)·하단(법령 고지) 오버레이 영역이 비어 있는가 — 거기에 텍스트/로고가 "
    "구워졌으면 오버레이와 충돌(critical). "
    "④ 명시 카피 외에 소품·기기 화면·간판·라벨·문서에 깨진 잔글씨나 임의의 'LOGO'/"
    "가짜 UI 텍스트가 구워졌는가 — 있으면 광고 품질을 해치므로 critical. "
    "⑤ 전반 가독성·구도(경미=warning). "
    'JSON 한 개만 출력: {"findings":[{"severity":"critical|warning","slot":"visual",'
    '"evidence":"무엇이 문제인지"}, ...]}. 결함이 없으면 findings는 빈 배열 [].'
)


def build_vision_instr(copy: dict, facts: str | None = None) -> str:
    """기대 카피(+금융 수치 정답)를 주입한 비전 검증 지시문. copy={headline,body,cta,...}."""
    expect = " / ".join(f'{k}="{v}"' for k, v in (copy or {}).items()
                        if k in ("headline", "body", "cta") and v)
    base = f"{_S2A_VISION_BASE}\n[기대 카피] {expect or '(없음)'}"
    if facts:
        # 금융 수치 환각 차단(실측: 베이크 금리카드가 5.0%/10만원 등 창작). factsheet 정답과
        # 대조해 불일치·창작 수치는 critical로 → _bake_with_retry가 재생성한다.
        base += (f"\n[반드시 정확해야 할 금융 수치(정답)] {facts}\n"
                 "이미지(특히 금리 카드)에 렌더된 금리·우대금리·가입기간·최소금액 등 숫자가 "
                 "위 정답과 다르거나(오독·창작·과장), 위 목록에 없는 금리·금액·기간 숫자가 새로 "
                 "그려져 있으면 severity=critical로 반드시 보고하세요(금융 표시광고 위반).")
    return base


# Task 4에서 정리 예정: steps.py·기존 테스트 import 보존을 위한 별칭.
S2A_VISION_INSTR = _S2A_VISION_BASE


# ── RICH_VECTOR_CHROME (히어로 우선 벡터 크롬, spec 2026-07-02) ──────────────

def build_hero_prompt(concept: str, mood_hint: str = "") -> str:
    """텍스트 프리 디자인 히어로 — 모든 마케팅 텍스트는 프론트 벡터 레이어가 얹는다."""
    lines = [concept]
    if mood_hint:
        lines.append(f"무드: {mood_hint}")
    lines.append(
        "이 이미지에는 **어떤 텍스트·글자·숫자·로고·워터마크도 절대 넣지 마세요**(전면 금지). "
        "간판·라벨·문서·기기 화면도 글자 없이(블랭크) 두세요. 텍스트는 이후 별도 레이어로 얹습니다.")
    lines.append(
        "텍스트 레이어를 얹을 **넓은 네거티브 스페이스(여백)**를 구도에 확보하세요: "
        "화면의 40~55%는 단순하고 차분한 영역(하늘·벽·보케·그라데이션)으로 비워 두고, "
        "피사체는 한쪽에 배치하세요.")
    lines.append(
        "오버레이 세이프존: **좌상단 모서리는 밝은 오프화이트로 깨끗이**, **최하단 가로 영역은 "
        "브랜드 색 솔리드 푸터 밴드**로 마감하되 그 안은 비워 두세요(로고·법령 고지 자리).")
    lines.append(
        "전체를 실제 금융 브랜드 광고 수준으로 마감하세요: 전문 광고 사진 품질의 자연광·"
        "시네마틱 라이팅과 얕은 심도, 고급스럽고 신뢰감 있는 색보정. "
        "저해상·클립아트·스톡 느낌은 피하세요.")
    return "\n".join(lines)


# vision 의미 레이아웃 — 픽셀 좌표를 시키면 부정확(실측)하므로 의미만 받고
# bbox는 layout_engine이 결정론으로 계산한다(spec §3.2).
SEMANTIC_LAYOUT_INSTR = (
    "이 이미지는 마케팅 포스터의 배경 히어로입니다. 텍스트 레이어를 얹기 위한 "
    "**의미 레이아웃**만 분석하세요. **픽셀 좌표는 절대 내지 마세요.**\n"
    "JSON 한 개만 출력(코드펜스·주석 금지):\n"
    '{"clear_zones": ["top-left"|"top-right"|"center-left"|"center-right"|"lower-third" 중 '
    "비어 있어 텍스트를 얹기 좋은 영역들], "
    '"busy_zones": [피사체·디테일로 복잡한 영역들(같은 어휘)], '
    '"palette": ["#RRGGBB" 히어로에서 뽑은 대표색 2~4개 — 첫째=텍스트 잉크로 쓸 진한 색, '
    '둘째=CTA 버튼용 포인트 색], '
    '"mood": "youth"|"premium"|"campaign" 중 히어로 무드에 맞는 것}'
)

# 텍스트 프리 히어로 게이트 — 베이크 모드의 카피 정확성 검증 대신 '글자 0'을 검증.
TEXTFREE_VISION_INSTR = (
    "이 이미지는 텍스트가 전혀 없어야 하는 포스터 배경 히어로입니다. 다음을 점검해 "
    "결함만 보고하세요: ① 어떤 글자·숫자·로고·워터마크·깨진 잔글씨라도 보이면 "
    "severity=critical(텍스트는 별도 레이어로 얹으므로 배경에 있으면 안 됨). "
    "② 인물이 있다면 손가락·손·얼굴 등 해부학적 왜곡(critical). "
    "③ 좌상단(로고)·하단(고지) 세이프존이 비어 있고 단순한가(침범=critical). "
    'JSON 한 개만: {"findings":[{"severity":"critical|warning","slot":"visual",'
    '"evidence":"..."}]}. 결함 없으면 빈 배열 [].'
)
