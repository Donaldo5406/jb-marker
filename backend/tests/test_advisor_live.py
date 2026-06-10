"""AnthropicAdvisorProvider 단위 — SDK 모킹으로 tool_use 응답 → DeployAdvisor 계약 변환 검증."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.deploy.advisor.live import AnthropicAdvisorProvider, _build_system


def _fake_response(blocks):
    return SimpleNamespace(content=[SimpleNamespace(**b) for b in blocks])


def test_build_system_embeds_ctx() -> None:
    sys = _build_system({"original_text": "수익률 5%", "disclosures": ["광고", "수신거부"]}, "sms")
    assert "수익률 5%" in sys
    assert "sms" in sys
    assert "광고" in sys


def test_chat_converts_text_block() -> None:
    p = AnthropicAdvisorProvider(api_key="x", model="m", ctx={"original_text": "x"}, channel="sms")
    fake = _fake_response([{"type": "text", "text": "안녕하세요"}])
    with patch("anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = fake
        out = p.chat(system="", messages=[{"role": "user", "content": "hi"}], tools=[])
    assert out["text"] == "안녕하세요"
    assert out["tool_calls"] == []


def test_chat_converts_tool_use_block() -> None:
    p = AnthropicAdvisorProvider(api_key="x", model="m", ctx={"original_text": "수익률 5%"}, channel="sms")
    fake = _fake_response([
        {"type": "text", "text": "다듬었습니다"},
        {"type": "tool_use", "name": "write_d2_copy", "input": {"package_id": "sms_ko", "adapted_text": "수익률 5%"}},
    ])
    with patch("anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = fake
        out = p.chat(system="", messages=[{"role": "user", "content": "짧게"}], tools=[])
    assert out["text"] == "다듬었습니다"
    assert len(out["tool_calls"]) == 1
    assert out["tool_calls"][0]["name"] == "write_d2_copy"
    assert out["tool_calls"][0]["input"]["adapted_text"] == "수익률 5%"


def test_chat_handles_empty_input() -> None:
    p = AnthropicAdvisorProvider(api_key="x", model="m", ctx={}, channel="sms")
    fake = _fake_response([
        {"type": "tool_use", "name": "read_review", "input": None},
    ])
    with patch("anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = fake
        out = p.chat(system="", messages=[{"role": "user", "content": "?"}], tools=[])
    assert out["tool_calls"][0]["input"] == {}
