"""LLM 출력·frontmatter 공용 파서 — 3벌 중복(_parse_json)·2벌 중복(_frontmatter) 통합 (T1 P1).

동작 보존: harness_brainstorming._parse_json / DesignHarness._parse_json /
core/legal_search._parse_json은 문자 그대로 동일 구현이었고, _frontmatter는
harness_design/harness_review 동일 복제였다. read_json_node는
`(store.get(p) or _Empty()).content_text` 패턴(_Empty 더미 2벌)을 대체한다.
"""
from __future__ import annotations

import json
import re

import yaml


def parse_json_block(text: str | None) -> dict:
    """LLM 출력에서 첫 JSON 객체를 견고하게 추출(코드펜스 제거·greedy 폴백)."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        # greedy: 최외곽 중괄호 구간(단일 JSON 객체 출력 가정). 비-JSON 조각은 {}.
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return {}
        try:
            return json.loads(m.group(0))
        except Exception:
            return {}


def parse_frontmatter(md: str | None) -> dict:
    """`--- YAML ---` frontmatter 블록 → dict. 없거나 깨지면 {}."""
    md = (md or "").lstrip()
    if not md.startswith("---"):
        return {}
    end = md.find("\n---", 3)
    block = md[3:end] if end > 0 else md[3:]
    try:
        return yaml.safe_load(block) or {}
    except Exception:
        return {}


def read_json_node(store, path: str) -> dict:
    """VFS 노드 content_text를 JSON dict로. 노드 부재·빈 내용은 {}."""
    node = store.get(path)
    return parse_json_block(node.content_text if node and node.content_text else "{}")
