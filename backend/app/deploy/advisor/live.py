"""AnthropicAdvisorProvider — 실 Claude messages-with-tools 호출.

- ctx(copy.meta.json) + channel을 system prompt에 embed → LLM이 read_review 없이도 컨텍스트 보유
- TOOL_SCHEMAS 그대로 Anthropic API에 전달, tool_use 블록을 DeployAdvisor가 기대하는
  `{"text": ..., "tool_calls": [{"name", "input"}]}` 형태로 변환
- 키 없을 때는 server.py 라우트가 _ScriptedAdvisorProvider로 fallback
"""
from __future__ import annotations

from typing import Any

from .prompt import SYSTEM_PROMPT
from .tools import TOOL_SCHEMAS


CHANNEL_LIMITS_HINT = {
    "sms": {"max_title_len": 0, "max_body_len": 90},
    "email": {"max_title_len": 80, "max_body_len": 600},
    "kakao": {"max_title_len": 40, "max_body_len": 1000},
    "naver": {"max_title_len": 30, "max_body_len": 400},
    "google": {"max_title_len": 30, "max_body_len": 400},
    "instagram": {"max_title_len": 40, "max_body_len": 400},
}


def _build_system(ctx: dict, channel: str) -> str:
    original = ctx.get("original_text", "")
    disclosures = ctx.get("disclosures", [])
    limits = CHANNEL_LIMITS_HINT.get(channel, {"max_body_len": 90})
    ctx_block = (
        f"\n\n## 현재 카드 컨텍스트\n"
        f"- 채널: {channel}\n"
        f"- 원본 카피: {original!r}\n"
        f"- 채널 한도: {limits}\n"
        f"- 필수 고지(코드가 자동 append, 본문 포함 금지): {disclosures}\n"
    )
    return SYSTEM_PROMPT + ctx_block


class AnthropicAdvisorProvider:
    """Anthropic messages-with-tools wrapper — DeployAdvisor 계약(.chat) 충족."""

    def __init__(self, *, api_key: str, model: str, ctx: dict, channel: str) -> None:
        self._api_key = api_key
        self._model = model
        self._ctx = ctx
        self._channel = channel

    def chat(self, *, system, messages, tools) -> dict[str, Any]:
        from anthropic import Anthropic

        client = Anthropic(api_key=self._api_key)
        sys_text = _build_system(self._ctx, self._channel)
        resp = client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=sys_text,
            tools=TOOL_SCHEMAS,
            messages=[{"role": m["role"], "content": m["content"]} for m in messages],
        )

        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        for block in resp.content:
            btype = getattr(block, "type", None)
            if btype == "text":
                text_parts.append(getattr(block, "text", ""))
            elif btype == "tool_use":
                tool_calls.append(
                    {"name": getattr(block, "name", ""), "input": getattr(block, "input", {}) or {}}
                )
        usage = None
        u = getattr(resp, "usage", None)
        if u is not None:
            usage = {
                "input_tokens": int(getattr(u, "input_tokens", 0) or 0),
                "output_tokens": int(getattr(u, "output_tokens", 0) or 0),
            }
        out: dict[str, Any] = {"text": "".join(text_parts), "tool_calls": tool_calls}
        if usage is not None:
            out["_usage"] = usage
            out["_model"] = self._model
        return out
