"""결정론 레이아웃 엔진 — vision 의미 레이아웃 → vector_chrome slots (spec §3.2).

LLM에 픽셀 bbox를 직접 시키면 좌표가 부정확하다(실측). 그래서 vision은 의미
(clear_zones·palette·mood)만 내고, 여기서 그리드 위 정확 bbox를 계산한다.
순수 모듈: provider/IO 무의존 — 재현성·테스트 용이가 목적이라 랜덤·시간 사용 금지.
수치·라벨은 호출자가 factsheet에서 그라운딩해 넘긴 facts만 사용(창작 금지)."""
from __future__ import annotations

import re

# 프론트 fontStack.BUNDLED_FONTS와 char-for-char 일치(계약).
MOOD_FONTS = {
    "youth": ("GmarketSansBold", "Pretendard"),
    "premium": ("NanumMyeongjo", "Pretendard"),
    "campaign": ("NanumPenScript", "Pretendard"),
}
_DEFAULT_DISPLAY = "Pretendard"

# vision 실패/스키마 불충족 시 폴백 — 파이프라인은 vision 없이도 유효 레이아웃을 낸다.
DEFAULT_SEMANTIC = {"clear_zones": ["top-left"], "busy_zones": [],
                    "palette": [], "mood": "youth"}

# 프론트 iconRegistry.ICON_KEYS 미러(허용목록 밖 키는 프론트가 percent로 폴백하지만,
# 백엔드가 애초에 허용 키만 내는 것이 계약).
_FACT_ICON = {"우대금리": "trending-up", "가입기간": "calendar",
              "최소가입금액": "coins", "예금자보호": "shield"}

_BASE_W = 1080
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _dims(aspect: str) -> tuple[int, int]:
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)\s*$", aspect or "")
    if not m:
        return _BASE_W, _BASE_W
    w, h = float(m.group(1)), float(m.group(2))
    if w <= 0 or h <= 0:
        return _BASE_W, _BASE_W
    return _BASE_W, round(_BASE_W * h / w)


def _palette(sem: dict) -> list:
    return [c for c in (sem.get("palette") or []) if isinstance(c, str) and _HEX.match(c)]


def _rate_lines(facts: dict) -> list:
    """금리 카드 라인 — 정적 라벨 + 그라운딩 값 연결만(_benefit_chips 패턴)."""
    lines = []
    if facts.get("최고금리"):
        lines.append({"text": "최고금리", "style": "label"})
        lines.append({"text": facts["최고금리"], "style": "figure"})
    elif facts.get("기본금리"):
        lines.append({"text": "기본금리", "style": "label"})
        lines.append({"text": facts["기본금리"], "style": "figure"})
    caption = " · ".join(facts[k] for k in ("기본금리", "우대금리")
                         if facts.get(k) and facts.get("최고금리"))
    if caption:
        lines.append({"text": caption, "style": "caption"})
    return lines


def _benefit_items(facts: dict) -> list:
    items = []
    for label in ("우대금리", "가입기간", "최소가입금액"):
        if facts.get(label):
            items.append({"icon_key": _FACT_ICON.get(label, "percent"),
                          "title": label, "desc": facts[label]})
    return items


def build_layout(semantic: dict, aspect: str, copy: dict, facts: dict) -> dict:
    """의미 레이아웃 + 그라운딩 facts → vector_chrome slots.

    수직 스택(겹침 없음, 비율 기반)이 골격. vision의 기여 = palette(색)·mood(폰트)·
    busy_zones(헤드라인 가독 scrim). logo 슬롯은 방출하지 않는다 — S2cBrand 소유."""
    sem = semantic or DEFAULT_SEMANTIC
    W, H = _dims(aspect)
    pal = _palette(sem)
    ink = pal[0] if pal else "#0B1324"
    accent = pal[1] if len(pal) > 1 else "#0066FF"
    display, body_font = MOOD_FONTS.get(sem.get("mood"), (_DEFAULT_DISPLAY, "Pretendard"))
    busy = bool(sem.get("busy_zones"))
    M = 80
    w = W - 2 * M
    slots = [{
        "role": "headline", "z": 3, "copy_key": "headline", "color": ink,
        "font_family": display, "weight": 800, "align": "left",
        "font_px": 84, "scrim": busy,
        "bbox": {"x": M, "y": round(0.14 * H), "w": w, "h": round(0.13 * H)},
    }]
    if copy.get("body"):
        slots.append({
            "role": "body", "z": 2, "copy_key": "body", "color": ink,
            "font_family": body_font, "weight": 400, "align": "left", "font_px": 36,
            "bbox": {"x": M, "y": round(0.29 * H), "w": w, "h": round(0.07 * H)},
        })
    slots.append({
        "role": "rate_card", "z": 2,
        "container": {"fill": "#FFFFFF", "radius": 16, "opacity": 0.94, "shadow": True},
        "font_family": body_font, "color": ink,
        "lines": _rate_lines(facts),
        "bbox": {"x": M, "y": round(0.38 * H), "w": w, "h": round(0.16 * H)},
    })
    slots.append({
        "role": "benefit_row", "z": 2, "font_family": body_font, "color": ink, "scrim": busy,
        "items": _benefit_items(facts),
        "bbox": {"x": M, "y": round(0.57 * H), "w": w, "h": round(0.11 * H)},
    })
    slots.append({
        "role": "cta_button", "z": 3, "copy_key": "cta",
        "fill": accent, "text_color": "#FFFFFF", "radius": 999,
        "font_family": display, "weight": 700, "font_px": 40,
        "bbox": {"x": M, "y": round(0.70 * H), "w": 520, "h": 96},
    })
    slots.append({
        "role": "disclosure", "z": 1, "copy_key": "disclosure",
        "color": "#FFFFFF", "font_px": 26, "font_family": body_font,
        "bbox": {"x": M, "y": H - 150, "w": w, "h": 110},
    })
    return {"render_mode": "vector_chrome", "slots": slots}
