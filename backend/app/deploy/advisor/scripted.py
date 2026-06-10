"""Scripted advisor — server.py 클로저에서 추출 (P4 T1, spec §8.1)."""
from __future__ import annotations


class ScriptedAdvisorProvider:
    """DeployAdvisor 계약(.chat) 충족용 데모 advisor — ctx·channel 주입.

    키워드(압축·짧·줄여·shorten·shorter·compress) 감지 시 채널 한도에 맞게
    원본을 공백 단위 truncate(부분집합 보장) → write_d2_copy tool_call.
    실 LLM 배선은 M7 또는 ANTHROPIC_API_KEY 도입 시 별도 wrapper로 교체.
    """

    SHORTEN_KEYWORDS = ("압축", "짧", "줄여", "shorten", "shorter", "compress")
    LIMITS = {"sms": 90, "email": 600, "kakao": 1000, "naver": 400, "google": 400, "instagram": 400}

    def __init__(self, *, ctx: dict, channel: str) -> None:
        self._ctx = ctx
        self._channel = channel

    def chat(self, *, system, messages, tools):
        last = messages[-1].get("content", "") if messages else ""
        wants_short = any(k in last for k in self.SHORTEN_KEYWORDS) or any(k in last.lower() for k in ("shorten", "shorter", "compress"))
        original = self._ctx.get("original_text", "")
        if wants_short and original:
            limit = self.LIMITS.get(self._channel, 90)
            tokens = original.split()
            adapted = ""
            for tok in tokens:
                candidate = (adapted + " " + tok).strip() if adapted else tok
                if len(candidate) > limit:
                    break
                adapted = candidate
            return {
                "text": f"원본 {len(original)}자 → {self._channel} 한도 {limit}자에 맞게 다듬었습니다.",
                "tool_calls": [{"name": "write_d2_copy", "input": {"adapted_text": adapted}}],
            }
        return {
            "text": f"카드 컨텍스트를 불러왔어요. '{last}'에 대해 더 구체적으로 말씀해 주시면 카피를 다듬어 드릴게요.",
            "tool_calls": [],
        }
