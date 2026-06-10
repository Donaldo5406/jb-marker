"""core/parsing — 하네스 3벌 중복이던 파서의 단일본 계약."""
import json

from app.core.parsing import parse_frontmatter, parse_json_block, read_json_node
from app.vfs.local import LocalVfsStore


def test_parse_json_block_plain():
    assert parse_json_block('{"a": 1}') == {"a": 1}


def test_parse_json_block_codefence():
    assert parse_json_block('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_block_greedy_fallback():
    assert parse_json_block('앞 {"a": 1} 뒤') == {"a": 1}


def test_parse_json_block_garbage_returns_empty():
    assert parse_json_block("설명 {role: bbox, not: valid json}") == {}
    assert parse_json_block("") == {}
    assert parse_json_block(None) == {}


def test_parse_frontmatter_basic():
    md = "---\ngoal: g\nlanguages: [ko, en]\n---\n본문"
    fm = parse_frontmatter(md)
    assert fm["goal"] == "g" and fm["languages"] == ["ko", "en"]


def test_parse_frontmatter_absent_or_broken():
    assert parse_frontmatter("그냥 본문") == {}
    assert parse_frontmatter("---\n: : broken: [\n---\n") == {}
    assert parse_frontmatter("") == {}


def test_read_json_node_missing_and_present(tmp_path):
    s = LocalVfsStore(storage_dir=str(tmp_path))
    s.create_run("r1")
    # VFS는 /{run}/{studio}/... 경로만 허용(validate_path) — design studio 경로 사용.
    assert read_json_node(s, "/r1/design/없는경로.json") == {}
    s.put("/r1/design/x.json", json.dumps({"k": "v"}),
          source="marker", mime="application/json")
    assert read_json_node(s, "/r1/design/x.json") == {"k": "v"}
