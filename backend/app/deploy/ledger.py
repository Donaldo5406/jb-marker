"""consent_ledger 로더 — 03 fixture(무수정) + pipa 필드 기본값 주입."""
from __future__ import annotations

import json
import pathlib

_DEFAULTS = {"collected_purpose": "marketing", "collected_days_ago": 30}


def load_ledger() -> list[dict]:
    # backend/app/deploy/ledger.py → backend/fixtures/consent_ledger.json
    # parents: [0]=deploy, [1]=app, [2]=backend
    path = pathlib.Path(__file__).parent.parent.parent / "fixtures" / "consent_ledger.json"
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return [{**_DEFAULTS, **r} for r in raw]
