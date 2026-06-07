"""시각 적법성 결정론 룰 — layout.spec의 시각 메타데이터를 한국 금융광고 시각규제로 검사.

한국 금융광고 규제는 '시각적 표현'을 명시적으로 규율한다(검증된 출처):
  - 금융소비자보호법 제22조 — 광고 필수 표시사항·균형 전달(글자 색·크기).
  - 금융투자협회 「광고선전에관한지침」 제5조④ — 경고문언 글자크기 ≥ 광고 최대글자의 30%,
    제5조③ 색상 대비, 제5조의2 안내문언 ≥ 본문 글자크기.
  - 금융위 「금융광고규제 가이드라인」 — 글자 색깔·크기로 혜택/불이익 균형·시인성.

MVP 3룰(결정론 — 비전 LLM 무관, 픽셀/치수 메타데이터 기반):
  R-VIS-1 고지 글자크기 — disclosure.font_px ≥ 최대 텍스트 글자크기 × DISCLOSURE_MIN_FONT_RATIO
  R-VIS-2 고지 대비   — disclosure 텍스트/배경 명도대비 ≥ MIN_CONTRAST_RATIO (WCAG AA)
  R-VIS-3 고지 존재   — disclosure 슬롯 + 카피가 존재(누락=critical)

⚠ 임계 수치는 config 기본값이다. 협회(은행연합회/금투협 등) 심의기준의 정확한 포인트
   수치는 비공개라 verbatim 확인 불가(unverified) → 합리적 근사치 + 공식 출처 첨부.
   배경이 이미지인 경우 contrast는 spec의 bg_color(대표 배경 톤) 선언값으로 근사한다.

메타데이터(font_px/color/bg_color)가 없으면 해당 룰은 graceful skip(오탐 방지).
"""
from __future__ import annotations

# 임계값 — config 기본값(협회 심의기준 실수치 비공개 → 근사치 + 출처. 확인 필요).
DISCLOSURE_MIN_FONT_RATIO = 0.3   # 금투협 광고선전지침 §5④ 경고문언 ≥ 최대글자 30%
MIN_CONTRAST_RATIO = 4.5          # WCAG 2.1 AA(본문) — 협회 '시인성' 요건 근사

_SRC_KOFIA = "https://law.kofia.or.kr/service/law/lawFullScreenContent.do?seq=216&historySeq=591"
_SRC_FSC = "https://www.fsc.go.kr/po010101/76045"
_SRC_LAW_CONSUMER = "https://www.law.go.kr/법령/금융소비자보호에관한법률/제22조"

_TEXT_ROLES = ("headline", "body", "cta")


def _hex_to_rgb(c: str | None) -> tuple[int, int, int] | None:
    c = (c or "").strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        return None
    try:
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
    except ValueError:
        return None


def _rel_luminance(rgb: tuple[int, int, int]) -> float:
    def chan(v: int) -> float:
        s = v / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b = (chan(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg_hex: str | None, bg_hex: str | None) -> float | None:
    """WCAG 명도대비비(1.0~21.0). 색 파싱 실패 시 None(룰 graceful skip)."""
    fg, bg = _hex_to_rgb(fg_hex), _hex_to_rgb(bg_hex)
    if fg is None or bg is None:
        return None
    l1, l2 = _rel_luminance(fg), _rel_luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return round((hi + 0.05) / (lo + 0.05), 2)


def _slots_by_role(spec: dict) -> dict:
    out: dict = {}
    for s in spec.get("slots", []) or []:
        r = s.get("role")
        if r:
            out[r] = s
    return out


def _max_text_font(slots: dict) -> int | None:
    fonts = [slots[r].get("font_px") for r in _TEXT_ROLES
             if r in slots and isinstance(slots[r].get("font_px"), (int, float))]
    return max(fonts) if fonts else None


def evaluate_visual_compliance(spec: dict) -> list[dict]:
    """layout.spec(slots + copy + bg_color)를 3룰로 검사 → 위반 finding 리스트.

    각 finding: {rule, severity, slot, clause, official_source_url, evidence, metrics}.
    메타데이터(font_px/color)가 없으면 해당 룰 skip(오탐 방지). 위반 없으면 빈 리스트.
    """
    if not isinstance(spec, dict):
        return []
    findings: list[dict] = []
    slots = _slots_by_role(spec)
    disc = slots.get("disclosure")
    copy = spec.get("copy") or {}

    # R-VIS-3 고지 존재: disclosure 슬롯 + (copy가 있으면) 고지 카피가 비어있지 않아야 함.
    has_disc_copy = any((copy.get(l) or {}).get("disclosure") for l in copy)
    if disc is None or (copy and not has_disc_copy):
        findings.append({
            "rule": "R-VIS-3", "severity": "critical", "slot": "disclosure",
            "clause": "금융소비자보호법 제22조(광고 시 필수 표시사항)",
            "official_source_url": _SRC_LAW_CONSUMER,
            "evidence": "필수 고지(disclosure) 요소가 레이아웃에 없거나 카피가 비어 있습니다.",
            "metrics": {},
        })
        return findings   # 고지 자체가 없으면 글자크기·대비는 평가 불가 → 조기 반환.

    # R-VIS-1 고지 글자크기 ≥ 최대 텍스트 글자크기 × 비율
    disc_font = disc.get("font_px")
    max_font = _max_text_font(slots)
    if isinstance(disc_font, (int, float)) and max_font:
        ratio = disc_font / max_font
        if ratio < DISCLOSURE_MIN_FONT_RATIO:
            findings.append({
                "rule": "R-VIS-1", "severity": "warning", "slot": "disclosure",
                "clause": "금융투자협회 광고선전에관한지침 제5조④(경고문언 ≥ 최대글자 30%)",
                "official_source_url": _SRC_KOFIA,
                "evidence": (f"고지 글자크기 {disc_font}px가 최대 텍스트 {max_font}px의 "
                             f"{ratio:.0%}로 기준({DISCLOSURE_MIN_FONT_RATIO:.0%}) 미만입니다."),
                "metrics": {"disclosure_font_px": disc_font,
                            "max_text_font_px": max_font, "ratio": round(ratio, 2)},
            })

    # R-VIS-2 고지 대비 ≥ 4.5:1 (WCAG AA)
    cr = contrast_ratio(disc.get("color"), spec.get("bg_color"))
    if cr is not None and cr < MIN_CONTRAST_RATIO:
        findings.append({
            "rule": "R-VIS-2", "severity": "warning", "slot": "disclosure",
            "clause": "금융위 금융광고규제 가이드라인(글자 색·크기 균형·시인성)",
            "official_source_url": _SRC_FSC,
            "evidence": (f"고지 명도대비 {cr}:1가 기준({MIN_CONTRAST_RATIO}:1) 미만으로 "
                         f"시인성이 부족합니다."),
            "metrics": {"contrast_ratio": cr, "min_required": MIN_CONTRAST_RATIO},
        })
    return findings


def visual_compliance_summary(spec: dict) -> dict:
    """metadata.md 기록용 시각 컴플라이언스 메트릭 + 위반 요약(결정론).

    Design 산출물 metadata에 '시각적 묘사'를 추가하는 핵심 — 글자크기·대비·고지 위치 등
    측정 가능한 시각 속성을 기록해 Review가 비전 LLM 없이도 1차 판단할 수 있게 한다.
    """
    if not isinstance(spec, dict):
        spec = {}
    slots = _slots_by_role(spec)
    disc = slots.get("disclosure") or {}
    findings = evaluate_visual_compliance(spec)
    return {
        "disclosure_font_px": disc.get("font_px"),
        "max_text_font_px": _max_text_font(slots),
        "disclosure_color": disc.get("color"),
        "bg_color": spec.get("bg_color"),
        "disclosure_contrast": contrast_ratio(disc.get("color"), spec.get("bg_color")),
        "violations": [{"rule": f["rule"], "severity": f["severity"],
                        "evidence": f["evidence"]} for f in findings],
        "passed": not findings,
    }
