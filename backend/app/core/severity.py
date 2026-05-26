"""severity 판정·게이트 산정·R2 키워드 안전망 (03 nodes/i18n_equiv.py 이식+M5 강화)."""
from __future__ import annotations


EXAGGERATION_TOKENS: list[str] = [
    "tốt nhất", "số một", "chắc chắn sinh lời",
    "lợi nhuận cao nhất", "không rủi ro", "chắc chắn có lời",
    "最高收益", "保证盈利", "稳赚", "零风险", "收益最高",
]

DISCLOSURE_I18N: dict[str, dict[str, list[str]]] = {
    "미래 수익 보장 아님": {
        "vi": ["không đảm bảo", "không bảo đảm lợi nhuận"],
        "zh": ["不保证收益", "不保证未来收益"],
        "en": ["not guaranteed", "no guarantee of future"],
    },
    "세전 금리, 우대조건 충족 시": {
        "vi": ["lãi suất trước thuế", "điều kiện ưu đãi"],
        "zh": ["税前利率", "满足优惠条件"],
        "en": ["pre-tax rate", "preferential conditions apply"],
    },
}


def detect_exaggeration(body: str) -> bool:
    """과장 키워드(03 EXAGGERATION_TOKENS) 검출 — R2 안전망."""
    body_lower = (body or "").lower()
    return any(tok.lower() in body_lower for tok in EXAGGERATION_TOKENS)


def find_missing_disclosures(body: str, lang: str,
                              required_disclosures: list[str]) -> list[str]:
    """필수고지가 번역체에 보존됐는지 키워드 매핑으로 안전망 검사."""
    body_lower = (body or "").lower()
    missing: list[str] = []
    for disc in required_disclosures:
        keywords = DISCLOSURE_I18N.get(disc, {}).get(lang, [])
        if not keywords:
            continue  # 매핑 없으면 안전망 미적용(LLM 판정에 위임)
        if not any(kw.lower() in body_lower for kw in keywords):
            missing.append(disc)
    return missing


# 5트리거 — spec §7.3·§5.4 동일
_DEMOTION_TRIGGERS = ("live_unavailable", "parse_failed", "vision_failed",
                      "step_failed", "vision_skipped")


def _trigger_active(flags: dict, key: str) -> bool:
    v = flags.get(key)
    if v is None or v is False:
        return False
    if isinstance(v, (list, tuple, str)) and len(v) == 0:
        return False
    return True


def compute_gate(verdicts: list[dict], *, flags: dict) -> dict:
    """게이트 산정 + 5트리거 WARN 강등 (spec §5.4·§7.3).

    Args:
        verdicts: R1+R2의 verdict 봉투 리스트(각 dict는 'severity' 필수).
        flags: graceful 표시 플래그 dict.

    Returns:
        {"status": "BLOCKED|WARN|PASS", "critical_count": N, "warning_count": M}
    """
    critical = sum(1 for v in verdicts if v.get("severity") == "critical")
    warning = sum(1 for v in verdicts if v.get("severity") == "warning")

    if critical > 0:
        status = "BLOCKED"
    elif (critical + warning) == 0:
        status = "PASS"
    else:
        status = "WARN"

    # PASS 강등: 5트리거 중 하나라도 → WARN. BLOCKED은 강등 무관.
    if status == "PASS":
        if any(_trigger_active(flags, k) for k in _DEMOTION_TRIGGERS):
            status = "WARN"

    return {"status": status, "critical_count": critical, "warning_count": warning}
