"""Mock 포스터 fixture 생성기(spec 2026-07-03 D1) — 실 Gemini 2K로 상태별 포스터 사전 베이크.

실 파이프라인과 동일한 build_director_prompt·facts·chips를 재사용해 드리프트를 막는다.
사용: (backend/) GOOGLE_API_KEY 주입 후  python -X utf8 scripts/gen_demo_posters.py [state ...]
      state 생략 = 전체(bg violating violating_gold final v2). 재생성은 상태명 지정.
비밀값 출력 금지 — 키는 env로만 읽는다.
"""
from __future__ import annotations

import copy
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import load_settings                                     # noqa: E402
from app.gateway.design.directing import build_director_prompt           # noqa: E402
from app.gateway.design.steps import (_benefit_chips, _facts_from_factsheet,  # noqa: E402
                                      _frontmatter)
from app.providers import demo_fixtures as F                             # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "references", "design")
MAX_BYTES = 10 * 1024 * 1024   # HF Space 안전선 — 초과 시 1080폭 다운스케일
# PLAN_MD frontmatter palette와 동기(골드는 넣지 않는다 — 2×2 골드 축 오염 가드, spec 참조).
TOKENS = {"palette": ["#00857C", "#0B2B5B", "#FFFFFF"],
          "typography": {"heading": "Pretendard Bold", "body": "Pretendard"},
          "visual_mood": "신뢰감 있고 친근한 금융 성장"}

_BG_PROMPT = (
    "당신은 대한민국 1군 금융광고 스튜디오의 아트디렉터입니다. 텍스트가 단 한 글자도 없는 "
    "프리미엄 은행 포스터 배경 한 장을 완성하세요.\n\n[포맷] 4:5 세로형.\n\n"
    "[디자인] 밝은 오프화이트(#F2EFE9) 기조의 추상적 금융 성장 이미지 — JB 그린(#00857C) "
    "포인트, 부드러운 그라데이션과 기하 요소. 글자·숫자·로고·워터마크 절대 금지.\n\n"
    "[레이아웃] 최상단 좌측 모서리: 아무것도 그리지 않은 밝고 단순한 빈 배경 영역(로고 "
    "오버레이 자리). 최하단 가로 스트립: 글자가 단 하나도 없는 어두운 단색 마감 밴드(고지 "
    "오버레이 자리).")


def _spec_for(state: str) -> dict:
    base = F.LAYOUT_SPEC_V2 if state.endswith(("gold", "v2")) else F.LAYOUT_SPEC
    spec = copy.deepcopy(base)
    ko = F.COPY_VIOLATING["ko"] if state.startswith("violating") else F.COPY["ko"]
    spec["copy"] = {"ko": dict(ko)}
    return spec


def _prompt_for(state: str) -> str:
    if state == "bg":
        return _BG_PROMPT
    fm = _frontmatter(F.PLAN_MD)
    facts = _facts_from_factsheet(fm.get("factsheet") or {})
    # 디자인 시스템의 "아이콘 네 개가 한 세트" 디렉티브와 칩 수를 맞춘다 — 라벨 2개만 주면
    # 모델이 빈 칩을 창작("혜택 3"/중복 라벨, 1차 생성 실측). 추가 2개는 spec 근거·무수치:
    # SPEC_MD key_messages "모바일 비대면 간편 가입" · disclosures "예금자보호".
    chips = list(_benefit_chips(facts)) + ["모바일 간편가입", "예금자보호"]
    prompt = build_director_prompt(_spec_for(state), TOKENS, facts, chips, "ko")
    # 실측 결함 보강(1~2차 생성): 'LOGO' 플레이스홀더 베이크·배경 차트 잔글씨 수치·골드본
    # 캘리그래피 질감 미달 — 스크립트 한정 추가 규칙(파이프라인 프롬프트는 불변).
    prompt += (
        "\n\n[추가 절대 규칙 — 위반 시 실패]\n"
        "- 'LOGO' 등 로고 플레이스홀더 글자·박스를 절대 그리지 마세요. 좌상단은 아무 표기 "
        "없는 완전한 빈 배경입니다.\n"
        "- 배경의 차트·스크린·그래프에는 숫자·퍼센트·글자를 일절 넣지 마세요(흐릿한 잔글씨 "
        "포함 금지) — 곡선과 막대 형태만.")
    if "#FFD166" in prompt:
        prompt += ("\n- 헤드라인은 반드시 붓펜으로 쓴 손글씨 캘리그래피 질감(필압·번짐이 "
                   "보이는 브러시 스트로크)의 골드(#FFD166)로 — 매끈한 디지털 산세리프 금지.")
    return prompt


def _save(state: str, png: bytes) -> None:
    from PIL import Image
    # 모델이 JPEG 바이트를 반환할 수 있다(실측) — 파이프라인·테스트 계약은 PNG
    # (확장자·매직·mime 일치)이므로 항상 PNG로 변환해 저장한다.
    im = Image.open(io.BytesIO(png))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    png = buf.getvalue()
    if len(png) > MAX_BYTES:
        im = im.resize((1080, round(1080 * im.height / im.width)))
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        png = buf.getvalue()
    name = "poster_bg.png" if state == "bg" else f"poster_{state}.png"
    path = os.path.join(OUT_DIR, name)
    with open(path, "wb") as f:
        f.write(png)
    print(f"{name}: {len(png):,} bytes")


def main() -> None:
    from app.providers.registry import get_provider
    provider = get_provider("google", load_settings())
    states = sys.argv[1:] or ["bg", "violating", "violating_gold", "final", "v2"]
    for st in states:
        print(f"== {st} 생성(2K) ==")
        png = provider.generate_image(_prompt_for(st), aspect="4:5", image_size="2K")
        _save(st, png)


if __name__ == "__main__":
    main()
