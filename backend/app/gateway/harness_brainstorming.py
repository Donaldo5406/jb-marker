"""BrainstormingHarness — 멀티턴 대화로 spec→plan 생성(stateless 재개).

LLM 응답 프로토콜(JSON): {"reply": str, "document": str, "ask": {...}|null, "ready": bool}
- document = 갱신된 전체 산출물(frontmatter+본문). 멱등 재작성(전체 갱신).
"""
from __future__ import annotations

import json
import re

from ..providers.base import Message
from .harness import AskPayload, Harness, HarnessRequest, HarnessResult

REQUIRED_PLAN_FIELDS = {
    "creative_direction", "material_matrix", "slots", "image_concept",
    "copy_themes", "multinational", "languages", "factsheet", "disclosures",
}

PERSONA = (
    "당신은 금융 마케팅 캠페인 기획 전문가입니다. 타겟 세그멘테이션·메시지 전략·채널 믹스·"
    "카피 방향·컴플라이언스(표시광고·금융광고)·리서치 기반 의사결정에 능합니다. "
    "한 번에 하나의 핵심 질문만 던지며, 사용자와 대화하며 기획을 점진적으로 구체화합니다."
)

_PROTOCOL = (
    "\n\n반드시 아래 JSON 한 개만 출력하세요(코드펜스 없이):\n"
    '{"reply": "사용자에게 보일 대화 응답(필요 시 질문 하나)", '
    '"document": "갱신된 전체 문서(--- YAML frontmatter --- 다음 마크다운 본문)", '
    '"ask": null 또는 {"trigger":"a|b|c","question":"...","options":["..."]}, '
    '"ready": true/false}'
)


def _parse_json(text: str) -> dict:
    """LLM 출력에서 첫 JSON 객체를 견고하게 추출."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return {}
        return {}


def _frontmatter_keys(md: str) -> set[str]:
    md = (md or "").lstrip()
    if not md.startswith("---"):
        return set()
    end = md.find("\n---", 3)
    block = md[3:end] if end > 0 else ""
    keys = set()
    for line in block.splitlines():
        if line and not line[0].isspace() and ":" in line:
            keys.add(line.split(":", 1)[0].strip())
    return keys


class BrainstormingHarness(Harness):
    def system_prompt(self) -> str:
        return PERSONA

    def critic(self, plan_md: str) -> list[str]:
        return sorted(REQUIRED_PLAN_FIELDS - _frontmatter_keys(plan_md))

    # --- 상태 I/O (stateless 재개의 단일 소스) ---
    def _base(self, run_id: str) -> str:
        return f"/{run_id}/brainstorming"

    def _load_state(self, store, run_id: str) -> dict:
        n = store.get(f"{self._base(run_id)}/_state.json")
        if n and n.content_text:
            return json.loads(n.content_text)
        return {"stage": "A", "spec_locked": False, "plan_locked": False, "pending_ask": None}

    def _save_state(self, store, run_id: str, state: dict) -> None:
        store.put(f"{self._base(run_id)}/_state.json", json.dumps(state, ensure_ascii=False),
                  source="marker", mime="application/json")

    def _load_messages(self, store, run_id: str) -> list[dict]:
        n = store.get(f"{self._base(run_id)}/_messages.json")
        if n and n.content_text:
            return json.loads(n.content_text)
        return []

    def _save_messages(self, store, run_id: str, msgs: list[dict]) -> None:
        store.put(f"{self._base(run_id)}/_messages.json", json.dumps(msgs, ensure_ascii=False),
                  source="marker", mime="application/json")

    def handle_turn(self, req: HarnessRequest, *, provider, store) -> HarnessResult:
        # Task 6/7에서 stage A/B 구현. 골격에서는 NotImplemented 방지용 최소 분기.
        raise NotImplementedError("Task 6/7에서 구현")
