"""ReviewHarness — R0~R3 5-step 핸들러 (DesignHarness 패턴 미러).

상태 단일주인 = /{run}/review/_state.json. 텍스트 액터=handle_turn provider(선택).
비주얼 액터=생성 시 주입된 vision_provider(항상 google/Gemini 멀티모달).

spec: jb-marker/docs/specs/2026-05-26-m5-review-studio-design.md
"""
from __future__ import annotations

import json

import yaml

from ..providers.base import Message, Provider
from .harness import Harness, HarnessRequest, HarnessResult

STEPS = ("R0", "R1", "R2", "R3", "done")

PERSONA_A = (
    "당신은 한국 금융 마케팅 분야의 전문 법률 검토관입니다. "
    "(자세한 지시는 build_legal_messages가 구성)"
)
PERSONA_B = (
    "당신은 금융 마케팅 다국어 동등성 검토관입니다. "
    "ko 자산을 기준으로 다른 언어 자산이 필수고지를 보존하는지·과장/오역/누락이 없는지 검토합니다. "
    'JSON 한 개만: {"findings":[{"lang":"en","kind":"missing_disclosure|mistranslation|exaggeration|omission",'
    '"severity":"critical|warning","evidence":"...","disclosure":"..."}, ...]} '
    "필수고지 누락은 반드시 severity=critical."
)
PERSONA_C = (
    "당신은 금융 마케팅 검토 결과의 통합 reconciler입니다. "
    "R1 법률 finding과 R2 동등성 finding의 경합을 조정하고 중복을 제거하며 우선순위를 매깁니다. "
    'JSON 한 개만: {"recommendations":[{"asset_id":"...","lang":"ko|null","target":"image|text|video",'
    '"instruction":"...","priority":1,"related_verdict_ids":["..."]}, ...],'
    '"conflicts_resolved":[{"summary":"..."}, ...]}'
)


class _Empty:
    content_text = "{}"


def _empty():
    return _Empty()


def _frontmatter(md: str) -> dict:
    md = (md or "").lstrip()
    if not md.startswith("---"):
        return {}
    end = md.find("\n---", 3)
    block = md[3:end] if end > 0 else md[3:]
    try:
        return yaml.safe_load(block) or {}
    except Exception:
        return {}


class ReviewHarness(Harness):
    def __init__(self, *, vision_provider: Provider) -> None:
        self._vision_provider = vision_provider

    def _base(self, run_id: str) -> str:
        return f"/{run_id}/review"

    def _load_state(self, store, run_id: str) -> dict:
        n = store.get(f"{self._base(run_id)}/_state.json")
        if n and n.content_text:
            return json.loads(n.content_text)
        return {
            "step": "R0", "languages": ["ko"], "matrix": {},
            "bypass": {}, "acknowledged": False, "last_run_at": None,
            "live_unavailable": False, "parse_failed": False,
            "vision_failed": False, "step_failed": "",
            "vision_skipped": [], "dropped_findings_count": 0,
            "r2_skipped": "",
        }

    def _save_state(self, store, run_id: str, state: dict) -> None:
        store.put(f"{self._base(run_id)}/_state.json",
                  json.dumps(state, ensure_ascii=False),
                  source="marker", mime="application/json")

    def handle_turn(self, req: HarnessRequest, *, provider, store) -> HarnessResult:
        state = self._load_state(store, req.run_id)
        action = getattr(req, "action", None)
        if action == "restart":
            return self._restart(req, store, state)
        if action == "ack" and state["step"] == "done":
            return self._ack(req, store, state)
        if action == "regenerate":
            return self._regenerate(req, store, state)
        step = state["step"]
        if step == "done":
            return HarnessResult(
                text="이미 검토가 완료되었습니다. 재검토는 'restart'를 사용하세요.",
                output_path=f"{self._base(req.run_id)}/report.md",
                meta={"source": "marker", "step": "done"}, events=[])
        return self._dispatch(step, req, provider, store, state)

    def _dispatch(self, step, req, provider, store, state) -> HarnessResult:
        if step == "R0":
            return self._r0_setup(req, store, state)
        if step == "R1":
            return self._r1_legal(req, provider, store, state)
        if step == "R2":
            return self._r2_i18n(req, provider, store, state)
        if step == "R3":
            return self._r3_reconcile(req, provider, store, state)
        raise NotImplementedError(f"{step} 미구현 (알 수 없는 step)")

    # ----- 후속 task에서 채워질 step 핸들러들 -----
    def _r0_setup(self, req, store, state):
        raise NotImplementedError("Task 6에서 구현")

    def _r1_legal(self, req, provider, store, state):
        raise NotImplementedError("Task 7~10에서 구현")

    def _r2_i18n(self, req, provider, store, state):
        raise NotImplementedError("Task 11~12에서 구현")

    def _r3_reconcile(self, req, provider, store, state):
        raise NotImplementedError("Task 13~14에서 구현")

    def _restart(self, req, store, state):
        raise NotImplementedError("Task 15에서 구현")

    def _ack(self, req, store, state):
        raise NotImplementedError("Task 15에서 구현")

    def _regenerate(self, req, store, state):
        raise NotImplementedError("Task 15에서 구현")
