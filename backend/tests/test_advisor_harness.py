"""DeployAdvisor — 도구 화이트리스트 + grounding 통합."""
import json
from dataclasses import dataclass

import pytest

from app.deploy.advisor.chat import DeployAdvisor


class FakeVfs:
    def __init__(self):
        self.store: dict[str, str] = {}

    def get_text(self, path):
        return self.store.get(path)

    def put_text(self, path, content):
        self.store[path] = content


@dataclass
class ScriptedProvider:
    """tool_calls 미리 결정된 응답 리스트."""
    responses: list[dict]
    idx: int = 0

    def chat(self, *, system, messages, tools):
        out = self.responses[self.idx]
        self.idx += 1
        return out


def _seed_package(vfs, run_id, package_id):
    meta = {
        "original_text": "수익률 5% 광고 수신거부",
        "disclosures": ["광고", "수신거부"],
    }
    vfs.put_text(f"/{run_id}/deploy/packages/{package_id}/copy.meta.json", json.dumps(meta, ensure_ascii=False))


def test_write_d2_copy_grounding_ok():
    vfs = FakeVfs()
    _seed_package(vfs, "r1", "email_ko")
    provider = ScriptedProvider(responses=[{
        "text": "적응 완료",
        "tool_calls": [{"name": "write_d2_copy", "input": {"package_id": "email_ko", "adapted_text": "수익률 5% 광고 수신거부 안내"}}],
    }])
    h = DeployAdvisor(provider=provider, vfs_store=vfs, run_id="r1")
    res = h.handle_turn(package_id="email_ko", user_message="80자로 압축해줘")
    assert res["tool_results"][0]["status"] == "ok"
    saved = json.loads(vfs.get_text("/r1/deploy/packages/email_ko/copy.meta.json"))
    assert saved["grounding_check"] == "ok"


def test_write_d2_copy_grounding_fail_records_failures():
    vfs = FakeVfs()
    _seed_package(vfs, "r1", "email_ko")
    provider = ScriptedProvider(responses=[{
        "text": "적응 완료",
        "tool_calls": [{"name": "write_d2_copy", "input": {"package_id": "email_ko", "adapted_text": "수익률 9% 무조건"}}],
    }])
    h = DeployAdvisor(provider=provider, vfs_store=vfs, run_id="r1")
    res = h.handle_turn(package_id="email_ko", user_message="과장해줘")
    assert res["tool_results"][0]["status"] == "fail"
    assert any("number_mismatch" in f for f in res["tool_results"][0]["failures"])
    saved = json.loads(vfs.get_text("/r1/deploy/packages/email_ko/copy.meta.json"))
    assert saved["grounding_check"] == "fail"


def test_disallowed_tool_blocked_and_recorded():
    vfs = FakeVfs()
    _seed_package(vfs, "r1", "email_ko")
    provider = ScriptedProvider(responses=[{
        "text": "발송 시도",
        "tool_calls": [{"name": "dispatch", "input": {"channel": "email"}}],
    }])
    h = DeployAdvisor(provider=provider, vfs_store=vfs, run_id="r1")
    res = h.handle_turn(package_id="email_ko", user_message="발송해줘")
    assert res["tool_results"][0]["status"] == "blocked"
    transcript = vfs.get_text("/r1/deploy/advisor/transcripts/email_ko.jsonl")
    assert "tool_blocked" in transcript


def test_read_review_returns_context():
    vfs = FakeVfs()
    _seed_package(vfs, "r1", "email_ko")
    provider = ScriptedProvider(responses=[{
        "text": "확인",
        "tool_calls": [{"name": "read_review", "input": {"package_id": "email_ko"}}],
    }])
    h = DeployAdvisor(provider=provider, vfs_store=vfs, run_id="r1")
    res = h.handle_turn(package_id="email_ko", user_message="원본 보여줘")
    out = res["tool_results"][0]["output"]
    assert out["original_text"] == "수익률 5% 광고 수신거부"
