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


import json as _json
import re as _re

from ..providers.base import Message, Provider


PERSONA_A = (
    "당신은 한국 금융 마케팅 분야의 전문 법률 검토관입니다. "
    "주어진 마케팅 자산(헤드라인·바디·CTA·고지·콘티)에 대해 표시광고법·금융소비자보호법·"
    "금융광고규정 등 관련 법령을 동적으로 서칭(web_search 도구 사용)하여 위반/우려 사항을 찾습니다. "
    "반드시 공식 법령 출처(law.go.kr, moleg.go.kr, fss.or.kr, fsc.go.kr, elaw.klri.re.kr) URL만 인용하세요. "
    'JSON 한 개만 출력: {"findings":[{"location":{"slot":"headline|sub|cta|disclosure","lang":"ko"},'
    '"clause":"표시광고법 §3 ①","official_source_url":"https://law.go.kr/...",'
    '"severity":"critical|warning","evidence":"..."}, ...]} '
    "위반/우려 없으면 findings=[]를 반환하세요."
)


def _parse_json(text: str) -> dict:
    """M3/M4 _parse_json 미러 — 코드펜스 제거·greedy 폴백."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = _re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    try:
        return _json.loads(text)
    except Exception:
        m = _re.search(r"\{.*\}", text, _re.S)
        if not m:
            return {}
        try:
            return _json.loads(m.group(0))
        except Exception:
            return {}


def build_legal_messages(scene_copy: dict, metadata_md: str, whitelist: dict
                         ) -> tuple[str, list[Message], list[dict]]:
    """R1 텍스트+서칭 호출용 system/messages/tools 구성."""
    user_payload = {
        "scene_copy": scene_copy,
        "metadata": metadata_md,
        "whitelist_domains": whitelist.get("domains", []),
    }
    messages = [Message("user", _json.dumps(user_payload, ensure_ascii=False))]
    # provider-agnostic tool descriptor. Anthropic/Google는 자체 매핑.
    tools = [{"name": "web_search", "type": "web_search"}]
    return PERSONA_A, messages, tools


def search_and_filter(provider: Provider, scene_copy: dict, metadata_md: str,
                      whitelist: dict) -> tuple[list[dict], int, dict]:
    """R1 호출 1: 텍스트+서칭 → 화이트리스트 필터.

    Returns: (kept_findings, dropped_count, meta_flags)
    meta_flags ∈ {live_unavailable: bool, parse_failed: bool}
    """
    system, messages, tools = build_legal_messages(scene_copy, metadata_md, whitelist)
    meta = {"live_unavailable": False, "parse_failed": False}
    try:
        resp = provider.complete(messages, model=provider.name, system=system,
                                 tools=tools)
    except Exception:
        return [], 0, {"live_unavailable": True, "parse_failed": False}
    data = _parse_json(resp.text)
    if not data:
        meta["parse_failed"] = True
        return [], 0, meta
    findings = data.get("findings") or []
    kept, dropped = apply_whitelist(findings, whitelist)
    return kept, dropped, meta
