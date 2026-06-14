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


def _balanced_object(text: str) -> str | None:
    """첫 '{'부터 중괄호 균형이 맞는 첫 완전한 JSON 객체 구간을 슬라이스.

    문자열 리터럴(`"..."`)과 이스케이프(`\\"`)를 인식해 값 안의 중괄호를 깊이로
    세지 않는다 — greedy `\\{.*\\}`가 JSON 뒤에 붙은 인용 마크다운/후행 텍스트의
    `}`까지 삼켜 파싱을 깨뜨리던 문제를 막는다. 균형이 안 맞으면 None.
    """
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def parse_json_block(text: str | None) -> dict:
    """LLM 출력에서 첫 JSON 객체를 견고하게 추출.

    1) 코드펜스 제거 후 통째로 파싱.
    2) 실패 시 균형 중괄호로 첫 객체 구간만 잘라 파싱.
    모든 파싱은 strict=False — LLM이 문자열 값 안에 raw 개행/탭(제어문자)을 넣는
    흔한 프로토콜 위반을 허용해 빈 dict 폴백(=무응답 체감)으로 떨어지는 빈도를 줄인다.
    """
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    try:
        return json.loads(text, strict=False)
    except Exception:
        pass
    block = _balanced_object(text)
    if block is None:
        return {}
    try:
        return json.loads(block, strict=False)
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
