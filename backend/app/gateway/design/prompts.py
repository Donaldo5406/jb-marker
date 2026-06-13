"""Design 프롬프트 상수 — PERSONA·단계 지시문 (구 harness_design.py:41-79 이동, T3 P2)."""

PERSONA = (
    "당신은 금융 마케팅 시니어 아트디렉터입니다. 시각 위계·그리드·여백·CTA 배치·"
    "브랜드 일관성·컴플라이언스 톤에 능하며, 인물·배경·구도·조명·색온도를 아우르는 "
    "키비주얼 아트디렉션에도 능합니다. 단, 텍스트는 절대 비주얼 픽셀에 굽지 않고 "
    "레이어로 분리합니다. 레이아웃은 구조화 JSON으로만 출력합니다."
)

# [S1 Rough] 지시·JSON 예시 — PromptSpec.constraints 단일 원소(문자열은 인라인 시절과 동일, D6).
S1_INSTR = (
    "\n\n[S1 Rough] 아래 레퍼런스 레이아웃을 참고해 layout_spec(JSON)을 출력하세요. "
    "slots에는 반드시 headline·body·cta·disclosure 4개 역할을 모두 포함하고, "
    "각 슬롯은 role·bbox{x,y,w,h}·z·copy_key를 갖습니다. 텍스트는 copy[lang][key]에 둡니다. "
    "시각 적법성 검토를 위해 각 텍스트 슬롯에 font_px(정수)와 color(#RRGGBB)를, "
    "최상위에 bg_color(#RRGGBB, 배경 대표 톤)를 반드시 포함하세요. "
    "필수 고지(disclosure)는 본문 대비 충분히 크고(최대 글자의 30% 이상) 배경과 대비가 "
    "분명하도록(명도대비 4.5:1 이상) 설정하세요. "
    "또한 최상위에 visual_concept(문자열)을 **반드시** 포함하세요 — 키비주얼을 위한 상세 "
    "아트디렉션입니다: 피사체(인물 포함 시 포즈·표정·시선·연령대·복장)·배경·구도·조명·색감·"
    "분위기를 구체 서술하고, 텍스트 슬롯 bbox가 놓이는 영역은 저대비·저디테일(safe zone)로 "
    "두라고 명시하세요(텍스트 가독성 선확보). 텍스트/숫자/로고는 비주얼에 넣지 마세요(레이어 분리). "
    "tokens의 color_palette·typography·concept(있으면)를 색(color/bg_color)·폰트·톤·"
    "visual_concept에 반영하고, aspect는 tokens.aspect를 따르세요. 정확한 출력 형식 예시:\n"
    '{"reply":"...","ready":true,"layout_spec":{"aspect":"4:5","bg_color":"#F2EFE9",'
    '"visual_concept":"밝은 채광의 카페 창가, 20대 청년이 통장을 두 손으로 들고 정면을 보며 '
    '환하게 미소, 상반신, 따뜻한 색감, 우상단은 단순한 벽면(텍스트 safe zone), 텍스트 없음",'
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

# [S2a 비전 게이트] review_image용 — 텍스트-free 계약·인물 해부학·safe zone 점검.
# harness_review.py의 v1.png 비전 검증(:306-314)을 design 단계로 앞당긴 형태.
S2A_VISION_INSTR = (
    "이 이미지는 금융 마케팅 포스터의 AI 생성 키비주얼입니다. 텍스트는 별도 레이어로 "
    "합성될 예정이라 이미지 자체는 텍스트-free 계약입니다. 다음을 점검해 결함만 보고하세요: "
    "① 글자/숫자/로고/워터마크가 이미지에 렌더됐는지(계약 위반=critical). "
    "② 인물이 있다면 손가락 개수·손 형태·얼굴 등 해부학적 왜곡(왜곡=critical). "
    "③ 텍스트가 올라갈 여백(safe zone)이 과도하게 복잡해 가독성을 해치는지(경미=warning). "
    'JSON 한 개만 출력: {"findings":[{"severity":"critical|warning","slot":"visual",'
    '"evidence":"무엇이 문제인지"}, ...]}. 결함이 없으면 findings는 빈 배열 [].'
)
