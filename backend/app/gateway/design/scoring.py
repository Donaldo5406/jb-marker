"""Design 채점 — RUBRIC·score_layout(판정 순수함수)·run_critic(LLM 자기-크리틱) (T3 P2, spec §4.2).

score_layout = 구 DesignHarness.critic의 개명(T1 백로그 ① — '채점→판정'을
이름이 드러내게). run_critic = 구 DesignHarness._run_critic의 모듈 함수화.
"""
from __future__ import annotations

import json

from ...core.parsing import parse_json_block
from ...providers.base import Message
from ..prompt import PromptSpec
from .prompts import CRITIC_INSTR, PERSONA

RUBRIC = ("hierarchy", "grid", "whitespace", "cta",
          "compliance", "copy_visual", "brand")


def score_layout(scores: dict) -> dict:
    """7항목 1~5 채점 → pass 판정(평균≥3.5 그리고 단일≥2). (구 DesignHarness.critic)"""
    vals = [float(scores.get(k, 0)) for k in RUBRIC]
    avg = sum(vals) / len(vals) if vals else 0.0
    ok = avg >= 3.5 and min(vals) >= 2
    return {"scores": {k: scores.get(k) for k in RUBRIC},
            "avg": round(avg, 2), "pass": ok}


def run_critic(provider, spec) -> dict:
    """텍스트 provider에 7항목 자기-크리틱 JSON을 요청 → score_layout 판정(자문용)."""
    # 조립 순서(D6): persona → [자기-크리틱] 지시 — 인라인 시절과 동일.
    pspec = PromptSpec(persona=PERSONA,
                       constraints=[CRITIC_INSTR],
                       studio="design", step="critic")
    try:
        resp = provider.complete(
            [Message("user", json.dumps(spec, ensure_ascii=False))],
            system=pspec.assemble(), meta=pspec.meta)
        raw = (parse_json_block(resp.text).get("scores")) or {}
    except Exception:
        raw = {}
    # fake/비-JSON 경로는 {} → 누락 항목은 3(중립)으로 디폴트(오해성 하드제로 방지).
    scores = {k: raw.get(k, 3) for k in RUBRIC}
    return score_layout(scores)
