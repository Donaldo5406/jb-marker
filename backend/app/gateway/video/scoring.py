"""Video 채점 — RUBRIC·score_layout·run_critic(design 미러) + 타이밍(고지 노출시간) critic.

타이밍은 storyboard의 disclosure 레이어가 화면에 머무는 총 시간을 측정해 적법성을
판정한다(이미지 시각 룰에 시간 차원 추가, spec §2.3 R-VID-DISCLOSURE-TIME).
"""
from __future__ import annotations

import json

from ...core.parsing import parse_json_block
from ...providers.base import Message
from ..prompt import PromptSpec
from .prompts import CRITIC_INSTR, PERSONA

RUBRIC = ("hierarchy", "grid", "whitespace", "cta",
          "compliance", "copy_visual", "brand")

# 필수고지 최소 노출 시간(초). 잠정값 — spec §9 [미결](금융광고 영상 고지 기준 확인).
DISCLOSURE_MIN_SEC = 3.0


def score_layout(scores: dict) -> dict:
    """7항목 1~5 채점 → pass 판정(평균>=3.5 그리고 단일>=2). design score_layout 미러."""
    vals = [float(scores.get(k, 0)) for k in RUBRIC]
    avg = sum(vals) / len(vals) if vals else 0.0
    ok = avg >= 3.5 and min(vals) >= 2
    return {"scores": {k: scores.get(k) for k in RUBRIC},
            "avg": round(avg, 2), "pass": ok}


def run_critic(provider, spec) -> dict:
    """텍스트 provider에 7항목 자기-크리틱 JSON 요청 → score_layout 판정(자문용)."""
    pspec = PromptSpec(persona=PERSONA, constraints=[CRITIC_INSTR],
                       studio="video", step="critic")
    try:
        resp = provider.complete(
            [Message("user", json.dumps(spec, ensure_ascii=False))],
            system=pspec.assemble(), meta=pspec.meta)
        raw = (parse_json_block(resp.text).get("scores")) or {}
    except Exception:
        raw = {}
    scores = {k: raw.get(k, 3) for k in RUBRIC}
    return score_layout(scores)


def _disclosure_seconds(storyboard: dict) -> float | None:
    """모든 shot의 disclosure 레이어 노출시간(out-in) 합. 레이어 없으면 None."""
    total = 0.0
    found = False
    for shot in storyboard.get("shots", []) or []:
        for layer in shot.get("layers", []) or []:
            if layer.get("role") == "disclosure":
                found = True
                try:
                    total += max(0.0, float(layer.get("out", 0)) - float(layer.get("in", 0)))
                except (TypeError, ValueError):
                    pass
    return total if found else None


def evaluate_timing(storyboard: dict) -> list[dict]:
    """타이밍 적법성 위반 목록(결정론). 현재 룰: R-VID-DISCLOSURE-TIME."""
    secs = _disclosure_seconds(storyboard)
    if secs is None:
        return [{"rule": "R-VID-DISCLOSURE-TIME", "severity": "critical",
                 "evidence": "필수고지(disclosure) 레이어가 콘티에 없습니다."}]
    if secs < DISCLOSURE_MIN_SEC:
        return [{"rule": "R-VID-DISCLOSURE-TIME", "severity": "critical",
                 "evidence": f"고지 노출 {secs:.1f}s < 최소 {DISCLOSURE_MIN_SEC:.1f}s"}]
    return []


def timing_summary(storyboard: dict) -> dict:
    """metadata.md 기록용 타이밍 요약."""
    secs = _disclosure_seconds(storyboard)
    viols = evaluate_timing(storyboard)
    return {"passed": not viols, "disclosure_sec": secs, "violations": viols}
