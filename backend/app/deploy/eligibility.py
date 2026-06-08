"""D1: 다중 정책 결정론 평가 + 24-slot night-blocked calendar."""
from __future__ import annotations

from app.deploy.rules_engine import evaluate_recipient

# 정책 사람-라벨(사유 분해 UI). 법령 약칭과 조문.
POLICY_LABELS = {
    "infomatics": "§50 정보통신망법",
    "pipa": "§15·§16 개인정보보호법",
}
# BLOCK 상태 사람-라벨(사유칩 텍스트).
STATUS_LABELS = {
    "BLOCKED_OPT_OUT": "수신거부",
    "BLOCKED_NO_CONSENT": "마케팅 동의 없음",
    "BLOCKED_NIGHT": "야간 발송 제한",
    "BLOCKED_PURPOSE": "수집목적 외 이용",
    "BLOCKED_RETENTION": "보유기간 초과",
}
# 사유 분해 표시 순서(정보통신망법 → 개인정보보호법).
_POLICY_ORDER = ("infomatics", "pipa")


def _build_breakdown(excluded: list[dict]) -> list[dict]:
    """제외 수신자를 1차(가장 강한) 정책별로 묶어 사유 분해 생성.

    각 수신자는 primary policy로 1회만 집계 → count 합이 excluded 총수와 일치(§50+§15·§16).
    Returns: [{policy, label, citation, count, reasons:[{status,label,count}]}], _POLICY_ORDER 순.
    """
    groups: dict[str, dict] = {}
    for ex in excluded:
        pol = ex.get("policy", "unknown")
        g = groups.setdefault(pol, {
            "policy": pol,
            "label": POLICY_LABELS.get(pol, pol),
            # citation은 정책 yaml의 매핑 {law, article, source_url, quote}. 누락 시에도
            # dict로 통일(프론트가 객체로 렌더 — 문자열/객체 혼합으로 인한 크래시 방지).
            "citation": ex.get("citation") or {},
            "count": 0,
            "_reasons": {},
        })
        g["count"] += 1
        st = ex.get("status", "BLOCKED")
        g["_reasons"][st] = g["_reasons"].get(st, 0) + 1
    out: list[dict] = []
    ordered = [p for p in _POLICY_ORDER if p in groups] + [
        p for p in groups if p not in _POLICY_ORDER]
    for pol in ordered:
        g = groups[pol]
        reasons = [
            {"status": st, "label": STATUS_LABELS.get(st, st), "count": n}
            for st, n in sorted(g["_reasons"].items(), key=lambda kv: (-kv[1], kv[0]))
        ]
        out.append({"policy": g["policy"], "label": g["label"],
                    "citation": g["citation"], "count": g["count"], "reasons": reasons})
    return out


def build_eligibility(ledger: list[dict], policies: dict, *, send_hour: int = 10) -> dict:
    """수신자 전수 평가 + calendar 생성.

    Returns: {recipients, excluded, calendar, total, eligible_count, breakdown}
    """
    recipients = []
    excluded = []
    for r in ledger:
        res = evaluate_recipient(r, send_hour=send_hour, policies=policies)
        if res["status"].startswith("ALLOWED"):
            recipients.append({"id": r["id"], "lang": r["lang"], "status": res["status"]})
        else:
            excluded.append({
                "id": r["id"],
                "status": res["status"],
                "policy": res["policy"],
                "citation": res["citation"],
                "all_blocks": res.get("all_blocks", [res]),
            })

    night_citation = policies["infomatics"]["citation"]
    start = policies["infomatics"]["night_window"]["start_hour"]
    end = policies["infomatics"]["night_window"]["end_hour"]
    calendar = [
        {
            "hour": h,
            "blocked": (h >= start or h < end),
            "citation": night_citation if (h >= start or h < end) else None,
        }
        for h in range(24)
    ]

    return {
        "recipients": recipients,
        "excluded": excluded,
        "calendar": calendar,
        "total": len(ledger),
        "eligible_count": len(recipients),
        "breakdown": _build_breakdown(excluded),
    }
