"""VideoHarness — plan.md → V0~V3 영상 파이프라인 (PipelineOrchestrator 위임 셸).

DesignHarness(harness_design.py)와 동형. 제어 흐름=gateway/pipeline.py,
단계=video/steps.py, 프롬프트=video/prompts.py, 채점=video/scoring.py.
상태 단일주인 = /{run}/video/_state.json. 비주얼 액터=V2aFootage 생성자 주입.
"""
from __future__ import annotations

from ..core.lang import normalize_languages
from .harness import Harness, HarnessRequest, HarnessResult
from .pipeline import PipelineOrchestrator, StepContext
from .state import load_state, save_state
from .video.steps import (  # noqa: F401  (테스트 표면 re-export)
    CRITIC_STEPS, GATED_STEPS, STEP_CLASSES, STEPS,
    V0Setup, V1Storyboard, V2aFootage, V2bCopy, V2cBrand, V3Final,
)


class VideoHarness(Harness):
    def __init__(self, *, video_provider) -> None:
        self._video_provider = video_provider
        self._orch = PipelineOrchestrator(
            (V0Setup(), V1Storyboard(), V2aFootage(video_provider),
             V2bCopy(), V2cBrand(), V3Final()),
            studio="video",
            done_text="영상 콘티를 확정했습니다. 검토(review) 단계로 진행할 수 있습니다.",
            done_output="metadata.md",
            save_state=self._save_state)

    def system_prompt(self) -> str:
        from .video.prompts import PERSONA
        return PERSONA

    def _base(self, run_id: str) -> str:
        return f"/{run_id}/video"

    def _load_state(self, store, run_id: str) -> dict:
        st = load_state(store, run_id, "video", default_factory=lambda: {
            "step": "V0", "gate": None, "confirmed": {}, "bypass": {},
            "languages": ["ko"]})
        st.setdefault("gate", None)
        st["languages"] = normalize_languages(st.get("languages"))
        return st

    def _save_state(self, store, run_id: str, state: dict) -> None:
        save_state(store, run_id, "video", state)

    def handle_turn(self, req: HarnessRequest, *, provider, store) -> HarnessResult:
        state = self._load_state(store, req.run_id)
        ctx = StepContext(req=req, provider=provider, store=store, state=state,
                          base=self._base(req.run_id))
        return self._orch.handle_turn(ctx)
