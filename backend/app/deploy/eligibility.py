"""D1: 다중 정책 결정론 평가 + 24-slot night-blocked calendar."""
from __future__ import annotations

from app.deploy.rules_engine import evaluate_recipient


def build_eligibility(ledger: list[dict], policies: dict, *, send_hour: int = 10) -> dict:
    """수신자 전수 평가 + calendar 생성.

    Returns: {recipients: [...], excluded: [...], calendar: [...], total: int, eligible_count: int}
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
    }
