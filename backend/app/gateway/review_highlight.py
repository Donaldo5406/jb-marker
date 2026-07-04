# backend/app/gateway/review_highlight.py
"""Review 하이라이트 — 지오메트리 유틸 + self-contained HTML 조립기.

verdict의 정규화 bbox(0~1)를 포스터 이미지 위 마커펜 오버레이 HTML로 만든다.
이미지는 base64 data URI로 인라인 → iframe 네트워크 요청 0(인증·CORS 무관, PreviewFrame 관례).
좌표 해결(authored/slot)은 harness가, HTML 조립은 여기가 담당(관심사 분리).
"""
from __future__ import annotations

import base64
import html as _html

_DEFAULT_CANVAS = (1080, 1350)
_BAKED_VISUAL = "design/design-system/components/visual/v1.png"


def clamp01(v: float) -> float:
    return 0.0 if v < 0 else 1.0 if v > 1 else float(v)


def _slots(layout_spec: dict) -> list[dict]:
    return layout_spec.get("slots", []) or []


def canvas_of(layout_spec: dict) -> tuple[int, int]:
    """background 슬롯 bbox로 캔버스(W,H) 추정. 없으면 기본 1080×1350."""
    for s in _slots(layout_spec):
        if s.get("role") == "background":
            b = s.get("bbox") or {}
            w, h = b.get("w"), b.get("h")
            if w and h:
                return int(w), int(h)
    return _DEFAULT_CANVAS


def slot_to_bbox_norm(slot: str, layout_spec: dict) -> dict | None:
    """슬롯 role의 정규화 bbox(0~1). 슬롯/캔버스 없으면 None."""
    W, H = canvas_of(layout_spec)
    if not W or not H:
        return None
    for s in _slots(layout_spec):
        if s.get("role") == slot:
            b = s.get("bbox") or {}
            try:
                return {
                    "x": clamp01(b["x"] / W), "y": clamp01(b["y"] / H),
                    "w": clamp01(b["w"] / W), "h": clamp01(b["h"] / H),
                }
            except (KeyError, TypeError, ZeroDivisionError):
                return None
    return None


def reviewed_image_for(asset_id: str, lang: str | None,
                       render_langs: frozenset = frozenset()) -> str:
    """verdict asset_id → 하이라이트할 실제 PNG 경로.

    원-레이어 구조: 헤드라인/바디/CTA는 배경 v1.png에 베이크됨. .scene·layout.spec 등
    비-PNG asset은 베이크된 v1.png로 매핑. 이미 PNG면 그대로(업로드 등).

    2026-07-05 GAP9: 합성 렌더(review/_render/{lang}.png — 고지·로고 오버레이 포함)가
    있으면 그것을 우선한다. 고지 지적을 v1(오버레이 미포함) 위에 그리면 '빈 자리에
    경고 박스'가 떠 시각근거가 자기모순이 됐다 — 심의가 본 화면을 그대로 하이라이트.
    """
    a = asset_id or ""
    if a.endswith(".png") or a.endswith(".jpg") or a.endswith(".jpeg"):
        return a
    eff = lang or "ko"
    if eff in render_langs:
        return f"review/_render/{eff}.png"
    return _BAKED_VISUAL


# --- HTML 조립기 -----------------------------------------------------------
# 포스터(base64 인라인) + rect 오버레이(정규화 0~1 → % 절대배치)를 self-contained
# HTML 문서로 조립한다. 외부 http/https 요청 없음(PreviewFrame과 동일 관례).

_STYLE = """
html,body{margin:0;height:100%;background:#0b0f14}
.stage{position:relative;width:100%;height:100%;display:flex;align-items:center;justify-content:center;padding:8px;box-sizing:border-box}
.frame{position:relative;display:inline-block;line-height:0}
.frame img{display:block;max-width:100%;max-height:100%;width:auto;height:auto;border-radius:8px}
.hl{position:absolute;box-sizing:border-box;border-radius:6px;animation:sweep .7s ease-out both}
.hl.crit{background:rgba(255,64,64,.30);box-shadow:inset 0 0 0 2px rgba(255,64,64,.9),0 0 14px 2px rgba(255,64,64,.4)}
.hl.warn{background:rgba(255,214,64,.42);box-shadow:inset 0 0 0 2px rgba(240,180,0,.95)}
.pin{position:absolute;top:-11px;left:-11px;width:22px;height:22px;border-radius:50%;color:#fff;font:700 12px/22px sans-serif;text-align:center;box-shadow:0 2px 5px rgba(0,0,0,.35)}
.hl.crit>.pin{background:#e0322f}.hl.warn>.pin{background:#c98a00}
@keyframes sweep{from{clip-path:inset(0 100% 0 0)}to{clip-path:inset(0 0 0 0)}}
@media(prefers-reduced-motion:reduce){.hl{animation:none}}
"""


def _pct(v: float) -> str:
    """정규화 값 → 퍼센트 문자열(불필요한 0 제거)."""
    s = f"{clamp01(v) * 100:.4f}".rstrip("0").rstrip(".")
    return s or "0"


def _rect_div(r: dict) -> str:
    cls = "crit" if r.get("severity") == "critical" else "warn"
    style = (f"left:{_pct(r['x'])}%;top:{_pct(r['y'])}%;"
             f"width:{_pct(r['w'])}%;height:{_pct(r['h'])}%")
    pin = _html.escape(str(r.get("pin", "")))
    return f'<div class="hl {cls}" style="{style}"><span class="pin">{pin}</span></div>'


def resolve_location(location: dict, *, asset_id: str, lang: str | None,
                     layout_spec: dict, fixtures: dict,
                     render_langs: frozenset = frozenset()) -> dict:
    """location에 image·bbox를 부착한 새 dict 반환(원본 불변).

    우선순위: 기존 bbox(live 비전) > authored fixture > slot 폴백 > 없음.
    render_langs: 합성 렌더가 존재하는 언어 집합 — 비-PNG asset의 하이라이트 대상을
    v1 대신 _render/{lang}.png로 승격(GAP9). authored fixture는 v1 키로도 폴백 조회
    (합성 렌더는 v1과 같은 4:5 정규화 좌표계 — background 슬롯 풀블리드).
    """
    out = dict(location)
    image = reviewed_image_for(asset_id, lang, render_langs)
    out["image"] = image
    if out.get("bbox"):                       # ① live 비전이 이미 채움
        return out
    slot = out.get("slot") or ""
    fx = (fixtures.get((image, slot, lang))            # ② authored 구절-tight
          or fixtures.get((_BAKED_VISUAL, slot, lang)))  # 합성 렌더 → v1 키 재사용
    if fx:
        out["bbox"] = dict(fx)
        return out
    sb = slot_to_bbox_norm(slot, layout_spec)  # ③ 슬롯 폴백
    if sb:
        out["bbox"] = sb
    return out                                 # ④ 미해결 → bbox 없음


def pin_sort_key(v: dict):
    """정규 정렬키 — critical 우선, 다음 verdict_id 사전순. 프론트(Task 5)와 동일 계약."""
    sev = 0 if v.get("severity") == "critical" else 1
    return (sev, v.get("verdict_id") or "")


def collect_rects(verdicts: list[dict], image: str) -> list[dict]:
    """image에 속하고 bbox 있는 verdict → 정렬·핀번호 부여한 rect 목록."""
    hits = [v for v in verdicts
            if (v.get("location") or {}).get("image") == image
            and (v.get("location") or {}).get("bbox")]
    hits.sort(key=pin_sort_key)
    rects = []
    for i, v in enumerate(hits, start=1):
        b = v["location"]["bbox"]
        rects.append({**b, "severity": v.get("severity", "warning"), "pin": i})
    return rects


def build_highlight_html(image_bytes: bytes, mime: str, rects: list[dict]) -> str:
    """포스터 base64 인라인 + rect 오버레이 self-contained HTML."""
    b64 = base64.b64encode(image_bytes or b"").decode("ascii")
    overlays = "".join(_rect_div(r) for r in (rects or []))
    return (
        "<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
        f"<style>{_STYLE}</style></head><body><div class='stage'><div class='frame'>"
        f"<img alt='review' src='data:{_html.escape(mime or 'image/png')};base64,{b64}'>"
        f"{overlays}</div></div></body></html>"
    )
