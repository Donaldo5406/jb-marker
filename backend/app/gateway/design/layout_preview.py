"""레이아웃 목업 렌더러 — layout.spec.json → self-contained HTML 시안 프리뷰.

시안 프리뷰 게이트(spec 2026-07-03 §1)의 순수 렌더러. 파이프라인이 진행되는 동안
콕핏 중앙에 현재 시안(레이아웃 존·실제 카피·팔레트·비주얼)을 결정론적으로 그린다
— LLM/이미지 호출 없음, 반복 비용 0.

- self-contained: 외부 네트워크 요청 0. 폰트는 system-ui 폴백 스택, 이미지는 base64
  data URI로만 인라인(``history/preview.py``의 ``_downscale_inline`` 재사용 — 중복 구현
  금지). CSS에 url()·http 참조 없음.
- 결정론: 타임스탬프·난수·환경 의존 없음. 같은 입력 → 같은 출력(단위 테스트로 고정).
- 방어: spec/slots/facts가 비거나 개별 slot이 dict가 아니거나 bbox가 없어도 크래시
  없이 (그 slot만 skip하고) 유효한 HTML을 반환한다. 모든 사용자 텍스트는 ``html.escape``,
  숫자는 float/int 강제 변환으로 인젝션을 차단한다.
"""
from __future__ import annotations

import base64
import math
import re

from ...history.preview import _downscale_inline, _esc

# 슬롯 role → 한글 라벨(프리뷰 존 라벨). 미지의 role은 원문 라벨로 폴백.
_ROLE_LABELS = {
    "headline": "헤드라인",
    "body": "바디",
    "cta": "CTA",
    "disclosure": "고지",
    "logo": "로고",
}

# CSS 컬러로 안전한 hex(#RGB·#RGBA·#RRGGBB·#RRGGBBAA)만 통과 — style 속성에 주입되는
# 색이 CSS 인젝션(외부 url()·추가 선언)으로 새지 않게 화이트리스트한다.
_HEX_RE = re.compile(r"^#(?:[0-9A-Fa-f]{3,4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")
_ASPECT_RE = re.compile(r"^\s*(\d{1,3})\s*:\s*(\d{1,3})\s*$")

_BASE_W = 1080.0   # 명목 캔버스 폭(bbox 좌표계 — S1_INSTR 예시가 1080 스케일).
_DISP_W = 480.0    # 프리뷰 캔버스 표시 폭(font_px 상대 스케일 기준).

_CSS = (
    "*{box-sizing:border-box}"
    "body{margin:0;padding:20px;font-family:system-ui,-apple-system,'Segoe UI',Roboto,"
    "'Helvetica Neue',Arial,'Malgun Gothic','Apple SD Gothic Neo',sans-serif;"
    "background:#f8fafc;color:#0b1324}"
    "h2{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#64748b;"
    "margin:20px 0 8px}"
    ".meta{color:#64748b;font-size:12px;margin:0 0 6px}"
    ".palette{display:flex;gap:10px;flex-wrap:wrap}"
    ".sw{display:flex;flex-direction:column;align-items:center;gap:3px}"
    ".chip{width:40px;height:40px;border-radius:8px;border:1px solid rgba(0,0,0,.1);display:block}"
    "code{font-size:10px;color:#475569}"
    ".concept{font-size:13px;line-height:1.5;color:#334155;max-width:640px;margin:0}"
    ".facts{display:flex;flex-wrap:wrap;gap:8px}"
    ".fact{background:#fff;border:1px solid rgba(0,0,0,.08);border-radius:8px;"
    "padding:6px 10px;display:flex;flex-direction:column;min-width:80px}"
    ".fk{color:#94a3b8;font-size:10px}"
    ".fv{font-weight:600;font-size:13px}"
    ".canvas{position:relative;width:100%;max-width:480px;margin-top:8px;"
    "border:1px solid rgba(0,0,0,.12);border-radius:12px;overflow:hidden;"
    "background-size:cover;background-position:center}"
    ".slot{position:absolute;display:flex;flex-direction:column;justify-content:flex-start;"
    "padding:3px 5px;border:1px dashed rgba(37,99,235,.55);background:rgba(255,255,255,.32);"
    "overflow:hidden}"
    ".role{position:absolute;top:1px;left:1px;font-size:9px;color:#2563eb;"
    "background:rgba(255,255,255,.82);padding:0 3px;border-radius:3px;pointer-events:none}"
    ".txt{font-weight:600;line-height:1.15;word-break:break-word;margin-top:12px}"
    ".empty{color:#94a3b8;font-size:13px;margin:0}"
)


def _num(v, default: float = 0.0) -> float:
    """숫자 강제 변환(인젝션 차단) — 변환 불가 시 default."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _safe_color(v, default: str = "") -> str:
    """hex 컬러만 통과, 그 외는 default — style 속성 CSS 인젝션·외부 url() 차단."""
    if isinstance(v, str) and _HEX_RE.match(v.strip()):
        return v.strip()
    return default


def _parse_aspect(aspect) -> tuple[int, int]:
    """"W:H" → (W, H) 양의 정수쌍. 파싱 실패 시 1:1."""
    m = _ASPECT_RE.match(str(aspect or ""))
    if m:
        w, h = int(m.group(1)), int(m.group(2))
        if w > 0 and h > 0:
            return w, h
    return 1, 1


def _hex_colors(values) -> list[str]:
    """리스트에서 hex 컬러만 순서 보존 추출."""
    out = []
    if isinstance(values, list):
        for c in values:
            sc = _safe_color(c)
            if sc:
                out.append(sc)
    return out


def build_layout_mock_html(
    spec: dict,
    tokens: dict,
    facts: dict,
    visual_png: bytes | None = None,
) -> str:
    """layout.spec.json(+tokens+facts[+visual])을 self-contained HTML 시안으로 렌더.

    - spec: ``rough/layout.spec.json`` (slots·copy·bg_color·visual_concept·aspect)
    - tokens: ``tokens.json`` (palette·color_palette·font·grid·typography·concept·visual_mood)
    - facts: ``_facts_from_factsheet`` 결과(label→value 문자열 dict — 금리 카드 미리보기)
    - visual_png: 선택적 v1.png 바이트. 있으면 캔버스 배경 이미지로 인라인(썸네일 다운스케일).
    """
    spec = spec if isinstance(spec, dict) else {}
    tokens = tokens if isinstance(tokens, dict) else {}
    facts = facts if isinstance(facts, dict) else {}

    aw, ah = _parse_aspect(spec.get("aspect") or tokens.get("aspect") or "1:1")

    # 주 언어 = spec.copy의 첫 언어(삽입순서=결정론) 또는 "ko".
    copy = spec.get("copy")
    copy = copy if isinstance(copy, dict) else {}
    prim = next(iter(copy.keys()), "ko")
    lang_copy = copy.get(prim)
    lang_copy = lang_copy if isinstance(lang_copy, dict) else {}

    # 유효 slot 수집(dict + bbox dict) + 좌표 최대 extent → 참조 캔버스 산정.
    valid = []
    mx = my = 0.0
    for s in (spec.get("slots") if isinstance(spec.get("slots"), list) else []):
        if not isinstance(s, dict):
            continue
        bbox = s.get("bbox")
        if not isinstance(bbox, dict):
            continue
        x, y = _num(bbox.get("x")), _num(bbox.get("y"))
        w, h = _num(bbox.get("w")), _num(bbox.get("h"))
        valid.append((s, x, y, w, h))
        mx = max(mx, x + w)
        my = max(my, y + h)

    # 참조 캔버스: aspect 유지 base(1080폭). bbox extent가 넘치면 비율 유지로 확장(박스가
    # 캔버스 밖으로 나가지 않게). 결정론(입력만으로 결정).
    ref_w = _BASE_W
    ref_h = _BASE_W * ah / aw
    if mx > ref_w or my > ref_h:
        scale = max(mx / ref_w if ref_w else 1.0, my / ref_h if ref_h else 1.0)
        ref_w *= scale
        ref_h *= scale

    boxes = []
    for (s, x, y, w, h) in valid:
        role = str(s.get("role") or "")
        label = _ROLE_LABELS.get(role, role or "슬롯")
        key = s.get("copy_key") or role
        tv = lang_copy.get(key) if isinstance(key, str) else None
        text = "" if tv is None else str(tv)
        left = (x / ref_w * 100) if ref_w else 0.0
        top = (y / ref_h * 100) if ref_h else 0.0
        bw = (w / ref_w * 100) if ref_w else 0.0
        bh = (h / ref_h * 100) if ref_h else 0.0
        fs = _num(s.get("font_px"))
        if fs <= 0:
            fs = h * 0.4   # font_px 누락 시 bbox 높이 기반 근사(결정론).
        disp = max(7.0, min(fs / ref_w * _DISP_W if ref_w else 7.0, 60.0))
        # 폰트-핏: 글자가 박스를 뚫고 글리프 중간에서 잘리면 "깨진" 프리뷰가 된다(사용자
        # 실측 피드백 2026-07-03). 한글 전각 근사(글자폭≈0.95em)로 필요 높이를 추정해
        # 박스 안에 들어가도록 결정론 축소(최대 3회 수렴, 하한 7px).
        boxpx_w = (w / ref_w * _DISP_W) if ref_w else float(_DISP_W)
        boxpx_h = (h / ref_w * _DISP_W) if ref_w else 40.0
        if text:
            for _ in range(3):
                per_line = max(1.0, boxpx_w / (disp * 0.95))
                lines = math.ceil(len(text) / per_line)
                need = lines * disp * 1.2 + 22   # +22 = role 태그 여백(12px)+패딩
                if need <= boxpx_h or disp <= 7.0:
                    break
                disp = max(7.0, disp * (boxpx_h / need) ** 0.5)
        color = _safe_color(s.get("color"), "#0b1324")
        boxes.append(
            f"<div class='slot' style='left:{left:.2f}%;top:{top:.2f}%;"
            f"width:{bw:.2f}%;height:{bh:.2f}%'>"
            f"<span class='role'>{_esc(label)}</span>"
            f"<span class='txt' style='font-size:{disp:.1f}px;color:{_esc(color)}'>"
            f"{_esc(text)}</span></div>"
        )
    boxes_html = "".join(boxes)

    # 캔버스 배경: bg_color + (있으면) visual_png 인라인 썸네일.
    bg_color = _safe_color(spec.get("bg_color"), "#f1f5f9")
    canvas_style = f"aspect-ratio:{aw}/{ah};background-color:{bg_color}"
    if visual_png:
        raw, mime = _downscale_inline(visual_png, "image/png")
        b64 = base64.b64encode(raw).decode("ascii")
        # CSS url은 큰따옴표 — 바깥 style 속성이 작은따옴표라 작은따옴표를 쓰면 속성값이
        # url( 에서 조기 종료돼 배경이 조용히 미렌더된다(리뷰 실측 버그).
        canvas_style += f';background-image:url("data:{mime};base64,{b64}")'

    # 상단: 팔레트 칩(tokens.palette + color_palette의 hex만).
    chip_colors = _hex_colors(tokens.get("palette")) + _hex_colors(tokens.get("color_palette"))
    chips = "".join(
        f"<div class='sw'><span class='chip' style='background:{_esc(c)}'></span>"
        f"<code>{_esc(c)}</code></div>"
        for c in chip_colors
    )
    cp = tokens.get("color_palette")
    color_note = cp if isinstance(cp, str) else ""

    # visual_concept 요약(없으면 tokens.concept 폴백).
    concept = spec.get("visual_concept") or tokens.get("concept") or ""

    # factsheet 수치 목록(금리 카드 미리보기).
    fact_rows = "".join(
        f"<div class='fact'><span class='fk'>{_esc(k)}</span>"
        f"<span class='fv'>{_esc(v)}</span></div>"
        for k, v in facts.items()
    )

    meta_bits = [f"비율 {aw}:{ah}"]
    if tokens.get("font"):
        meta_bits.append(f"폰트 {_esc(tokens['font'])}")
    if tokens.get("grid"):
        meta_bits.append(f"그리드 {_esc(tokens['grid'])}")
    if tokens.get("typography"):
        meta_bits.append(f"타이포 {_esc(tokens['typography'])}")
    meta_line = " · ".join(meta_bits)

    sections = [f"<div class='meta'>{meta_line}</div>"]
    if chips or color_note:
        sections.append("<h2>팔레트</h2>")
        if chips:
            sections.append(f"<div class='palette'>{chips}</div>")
        if color_note:
            sections.append(f"<p class='meta'>{_esc(color_note)}</p>")
    if concept:
        sections.append("<h2>비주얼 콘셉트</h2>")
        sections.append(f"<p class='concept'>{_esc(concept)}</p>")
    if fact_rows:
        sections.append("<h2>금리 카드</h2>")
        sections.append(f"<div class='facts'>{fact_rows}</div>")
    sections.append("<h2>레이아웃</h2>")
    canvas_inner = boxes_html or "<p class='empty'>레이아웃 슬롯이 아직 없습니다.</p>"
    sections.append(f"<div class='canvas' style='{canvas_style}'>{canvas_inner}</div>")

    body = "".join(sections)
    return (
        "<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<style>{_CSS}</style></head><body>{body}</body></html>"
    )
