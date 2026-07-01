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
        if getattr(req, "action", None) == "render":
            from .video.render import render_video
            lang = (state.get("languages") or ["ko"])[0]
            path = render_video(store, req.run_id, lang=lang)
            # 폴백 가시화(A2): render_video는 ffmpeg 부재/실패 시 28바이트 stub로 조용히
            # 폴백한다. 그 상태를 노드 meta에서 되읽어 라이브에서 정직하게 보고한다
            # — 그러지 않으면 깨진 mp4를 "렌더 성공"으로 알려 시연이 조용히 망가진다.
            # Mock(데모)의 stub은 의도된 결정론 산출이라 경고하지 않는다.
            rmeta = (getattr(store.get(path), "meta", None) or {})
            stub = rmeta.get("render") == "stub"
            if stub and not getattr(req, "mock", False):
                err = rmeta.get("render_error")
                text = ("영상 렌더가 정상 완료되지 않아 임시 파일로 대체됐습니다"
                        + (f" (원인: {err})" if err else " (ffmpeg 미탐지)")
                        + ". 렌더 환경(ffmpeg·CJK 폰트)을 확인한 뒤 다시 시도하세요.")
            else:
                text = "영상을 렌더했습니다. review/_render/final.mp4에서 확인하세요."
            return HarnessResult(
                text=text, output_path=path,
                meta={"source": "marker", "step": "render", "lang": lang,
                      "render": rmeta.get("render"),
                      "render_error": rmeta.get("render_error")},
                events=[{"type": "artifact", "path": path}])
        ctx = StepContext(req=req, provider=provider, store=store, state=state,
                          base=self._base(req.run_id))
        return self._orch.handle_turn(ctx)
