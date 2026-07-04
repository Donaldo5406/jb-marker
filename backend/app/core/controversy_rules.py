"""논란(사회 리스크) 결정론 룰 — 큐레이션 블랙리스트 기반 2티어 감지.

Tier-1(명백): 신호 매칭 즉시 critical(결정론, provider 불요) → mock 결정론의 뼈대.
Tier-2(맥락의존): signal + co_signal 결합 시에만 warning. 단독 신호는 무탐(오탐 방지).
              정밀 맥락 판정은 LLM(RC 라이브)이 보완한다.

블랙리스트: app/references/controversy/blacklist.yaml
중립성: 정치 판단 아님. '이 요소가 논란과 연관되어 의도와 무관하게 오해·물의를 부를 수 있다'는
       평판 리스크만 근거와 함께 표면화한다.
"""
from __future__ import annotations

import os

import yaml

_HERE = os.path.dirname(__file__)
_BLACKLIST_PATH = os.path.join(_HERE, "..", "references", "controversy", "blacklist.yaml")


def load_blacklist() -> list[dict]:
    with open(_BLACKLIST_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("entries", []) or []


def _norm(text: str) -> str:
    """정규화 — 소문자 + 중점·공백 제거(신호 부분문자열 매칭 안정화)."""
    return (text or "").lower().replace("·", ".").replace(" ", "")


def _finding(entry: dict, lang: str, matched: str, severity: str) -> dict:
    src = entry.get("source", "")
    return {
        "id": entry.get("id", ""),
        "category": entry.get("category", ""),
        "tier": entry.get("tier", 2),
        "severity": severity,
        "location": {"slot": "controversy", "lang": lang},
        "evidence": f"{entry.get('why_risky', '')} (선례: {src}; 신호: {matched})",
        "official_source_url": entry.get("source_url", "") or "",
    }


def evaluate(scene_copy: dict, *, blacklist: list[dict] | None = None) -> list[dict]:
    """scene_copy(언어별 슬롯 텍스트)에서 블랙리스트 신호를 결정론 검사 → controversy findings.

    Tier-1: 신호 하나라도 매칭 → severity_default(critical).
    Tier-2: 신호 + co_signal 동시 존재 → severity_default(warning). 단독 신호는 무탐.
    clean 카피면 빈 리스트.
    """
    entries = blacklist if blacklist is not None else load_blacklist()
    findings: list[dict] = []
    for lang, copy in (scene_copy or {}).items():
        if not isinstance(copy, dict):
            continue
        norm = _norm(" ".join(str(v) for v in copy.values()))
        for e in entries:
            hit = next((s for s in e.get("signals", []) if _norm(s) in norm), None)
            if not hit:
                continue
            if e.get("tier", 2) == 1:
                findings.append(_finding(e, lang, hit, e.get("severity_default", "critical")))
            else:
                co = next((c for c in e.get("co_signals", []) if _norm(c) in norm), None)
                if co:
                    findings.append(
                        _finding(e, lang, f"{hit}+{co}", e.get("severity_default", "warning")))
    return findings
