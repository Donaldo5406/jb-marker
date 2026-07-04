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


def reviewed_image_for(asset_id: str, lang: str | None) -> str:
    """verdict asset_id → 하이라이트할 실제 PNG 경로.

    원-레이어 구조: 헤드라인/바디/CTA는 배경 v1.png에 베이크됨. .scene·layout.spec 등
    비-PNG asset은 베이크된 v1.png로 매핑. 이미 PNG면 그대로(업로드 등).
    """
    a = asset_id or ""
    if a.endswith(".png") or a.endswith(".jpg") or a.endswith(".jpeg"):
        return a
    return _BAKED_VISUAL
