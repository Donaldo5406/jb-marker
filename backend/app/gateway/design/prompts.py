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


def build_vision_instr(copy: dict) -> str:
    """기대 카피를 주입한 비전 검증 지시문. copy={headline,body,cta,...}."""
    expect = " / ".join(f'{k}="{v}"' for k, v in (copy or {}).items()
                        if k in ("headline", "body", "cta") and v)
    return f"{_S2A_VISION_BASE}\n[기대 카피] {expect or '(없음)'}"


# Task 4에서 정리 예정: steps.py·기존 테스트 import 보존을 위한 별칭.
S2A_VISION_INSTR = _S2A_VISION_BASE
