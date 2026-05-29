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
