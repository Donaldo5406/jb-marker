"""
정책 yaml 다중 로더 + 정책별 평가 + 합성.

§50 우선순위: opt_out > no_consent(6mo 예외) > night > ALLOWED
§15·§16 우선순위: purpose_violation > retention_expired > ALLOWED
합성: 모두 ALLOWED여야 ALLOWED, 하나라도 BLOCK이면 정책별 사유 누적(가장 강한 BLOCK 첫 번째).
"""
from __future__ import annotations

import pathlib
import yaml

_BLOCK_PRIORITY = {
    "BLOCKED_OPT_OUT": 0,
    "BLOCKED_PURPOSE": 1,
    "BLOCKED_RETENTION": 2,
    "BLOCKED_NO_CONSENT": 3,
    "BLOCKED_NIGHT": 4,
}


def load_policies() -> dict[str, dict]:
    """`policies/*.yaml` 모두 로드 → {name: policy_dict}."""
    base = pathlib.Path(__file__).parent / "policies"
    out: dict[str, dict] = {}
    for path in sorted(base.glob("*.yaml")):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        out[data["name"]] = data
    return out


def evaluate_infomatics(r: dict, *, send_hour: int, policy: dict) -> dict:
    """§50: opt_out > no_consent > night > ALLOWED."""
    citation = policy["citation"]
    rid = r.get("id")

    if r["opt_out"]:
        return {"status": "BLOCKED_OPT_OUT", "citation": citation, "id": rid, "policy": "infomatics"}

    if not r["marketing_consent"]:
        last = r.get("last_same_product_days")
        if last is None or last > policy["same_product_exception_days"]:
            return {"status": "BLOCKED_NO_CONSENT", "citation": citation, "id": rid, "policy": "infomatics"}
        return {"status": "ALLOWED_EXCEPTION", "citation": citation, "id": rid, "policy": "infomatics"}

    start = policy["night_window"]["start_hour"]
    end = policy["night_window"]["end_hour"]
    is_night = send_hour >= start or send_hour < end
    if is_night and not r["night_consent"]:
        return {"status": "BLOCKED_NIGHT", "citation": citation, "id": rid, "policy": "infomatics"}

    return {"status": "ALLOWED", "citation": citation, "id": rid, "policy": "infomatics"}


def evaluate_pipa(r: dict, policy: dict) -> dict:
    """§15·§16: purpose_violation > retention_expired > ALLOWED."""
    citation = policy["citation"]
    rid = r.get("id")
    purpose = r.get("collected_purpose", "marketing")
    if purpose not in policy["allowed_purposes"]:
        return {"status": "BLOCKED_PURPOSE", "citation": citation, "id": rid, "policy": "pipa"}
    days = r.get("collected_days_ago", 0)
    if days > policy["retention_max_days"]:
        return {"status": "BLOCKED_RETENTION", "citation": citation, "id": rid, "policy": "pipa"}
    return {"status": "ALLOWED", "citation": citation, "id": rid, "policy": "pipa"}


def evaluate_recipient(r: dict, *, send_hour: int, policies: dict[str, dict]) -> dict:
    """다중 정책 합성. ALLOWED iff 모든 정책 ALLOWED. 아니면 가장 강한 BLOCK 채택."""
    results = []
    if "infomatics" in policies:
        results.append(evaluate_infomatics(r, send_hour=send_hour, policy=policies["infomatics"]))
    if "pipa" in policies:
        results.append(evaluate_pipa(r, policies["pipa"]))

    blocks = [x for x in results if x["status"].startswith("BLOCKED_")]
    if not blocks:
        # ALLOWED 또는 ALLOWED_EXCEPTION 중 가장 강한 라벨 채택(EXCEPTION 우선 표기)
        if any(x["status"] == "ALLOWED_EXCEPTION" for x in results):
            return next(x for x in results if x["status"] == "ALLOWED_EXCEPTION")
        return results[0]  # ALLOWED

    blocks.sort(key=lambda x: _BLOCK_PRIORITY.get(x["status"], 999))
    primary = blocks[0]
    primary["all_blocks"] = blocks  # 디버깅·report 용
    return primary


def evaluate_recipient_legacy(r: dict, send_hour: int, policy: dict) -> dict:
    """03 호환 wrapper — 단일 infomatics 정책 시그니처."""
    return evaluate_infomatics(r, send_hour=send_hour, policy=policy)
