"""consent_ledger 로더 — 03 fixture(무수정) + pipa 필드 기본값 주입."""
from __future__ import annotations

import json
import pathlib

_DEFAULTS = {"collected_purpose": "marketing", "collected_days_ago": 30}


def load_ledger() -> list[dict]:
    # consent_ledger.json은 ledger.py와 같은 디렉터리(app/deploy/)에 위치 —
    # 다른 런타임 자산(policies/·providers.yaml)과 동일하게 배포 이미지(COPY app ./app)에 포함됨.
    path = pathlib.Path(__file__).parent / "consent_ledger.json"
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return [{**_DEFAULTS, **r} for r in raw]


_TRUE = {"1", "true", "t", "y", "yes", "예", "o", "on"}


def _as_bool(v, default: bool = False) -> bool:
    if v is None or (isinstance(v, str) and not v.strip()):
        return default
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in _TRUE


def normalize_recipients(rows: list[dict]) -> list[dict]:
    """업로드 발송 명단(CSV→JSON)을 rules_engine이 읽는 스키마로 정규화.

    누락 필드는 안전 기본값으로 채운다 — 동의 컬럼이 없는 단순 명단은 '동의된 마케팅 명단'으로
    간주(marketing_consent=true·opt_out=false·night_consent=false)해 적격으로 잡되, CSV가 제공한
    동의/옵트아웃/야간 컬럼은 그대로 존중해 §50·§15·§16 판정이 동작하게 한다.
    """
    out: list[dict] = []
    for i, r in enumerate(rows or []):
        if not isinstance(r, dict):
            continue
        cda = str(r.get("collected_days_ago", "")).strip()
        out.append({
            **_DEFAULTS,
            "id": str(r.get("id") or r.get("email") or r.get("phone") or f"r{i:04d}"),
            "lang": str(r.get("lang") or "ko").strip().lower(),
            "marketing_consent": _as_bool(r.get("marketing_consent", r.get("consent")), default=True),
            "opt_out": _as_bool(r.get("opt_out"), default=False),
            "night_consent": _as_bool(r.get("night_consent"), default=False),
            "last_same_product_days": r.get("last_same_product_days"),
            **({"collected_purpose": str(r["collected_purpose"]).strip()} if r.get("collected_purpose") else {}),
            **({"collected_days_ago": int(cda)} if cda.isdigit() else {}),
        })
    return out
