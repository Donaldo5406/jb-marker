"""R1 법률 검토 — 라이브 동적 서칭 + 공식 법령 화이트리스트 필터.

spec §4.1·§5.2·§6.5. 라이브 키 부재 시 graceful — 빈 findings + live_unavailable=true 시그널.
"""
from __future__ import annotations

import json
import os
from urllib.parse import urlparse

_HERE = os.path.dirname(__file__)
_WHITELIST_PATH = os.path.join(_HERE, "..", "references", "legal", "whitelist.json")


def load_whitelist() -> dict:
    with open(_WHITELIST_PATH, encoding="utf-8") as f:
        return json.load(f)


def _domain_matches(host: str, allowed: list[str]) -> bool:
    host = (host or "").lower()
    return any(host == d or host.endswith("." + d) for d in allowed)


def apply_whitelist(findings: list[dict], whitelist: dict) -> tuple[list[dict], int]:
    """화이트리스트 외 출처 finding drop. (kept, dropped_count) 반환."""
    allowed = [d.lower() for d in whitelist.get("domains", [])]
    kept: list[dict] = []
    dropped = 0
    for f in findings:
        url = f.get("official_source_url") or ""
        host = urlparse(url).hostname or ""
        if host and _domain_matches(host, allowed):
            kept.append(f)
        else:
            dropped += 1
    return kept, dropped
