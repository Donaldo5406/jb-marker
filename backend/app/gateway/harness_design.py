"""DesignHarness — plan.md → S0~S3 디자인 파이프라인 (PipelineOrchestrator 위임 셸).

T3 P2: 제어 흐름=gateway/pipeline.py(P1 골격), 단계 구현=design/steps.py,
프롬프트=design/prompts.py, 채점=design/scoring.py. 이 모듈은 D6(테스트·registry
표면 보존)에 따라 DesignHarness와 호환 표면(STEPS·GATED_STEPS·CRITIC_STEPS·
next_step·_aspect_from_matrix·PERSONA·RUBRIC 등)을 같은 이름으로 유지하는
얇은 셸이다.

상태 단일주인 = /{run}/design/_state.json. 텍스트 액터=handle_turn provider(선택),
비주얼 액터=생성 시 주입된 image_provider(S2aVisual 생성자 주입).
"""
from __future__ import annotations

from ..core.lang import normalize_languages
from ..core.parsing import parse_json_block
# 호환 re-export(D6) — 테스트가 이 모듈 경로에서 임포트하는 표면(hd.PERSONA 등).
from .design.prompts import CRITIC_INSTR, PERSONA, S1_INSTR, S2B_INSTR  # noqa: F401
from .design.scoring import RUBRIC as _SCORING_RUBRIC
from .design.scoring import run_critic, score_layout  # noqa: F401
from .design.steps import (  # noqa: F401
    CRITIC_STEPS,
    DISCLOSURE_DISPLAY,
    GATED_STEPS,
    NOTICES,
    STEP_CLASSES,
    STEPS,
    S0Setup,
    S1Rough,
    S2aVisual,
    S2bCopy,
    S2cBrand,
    S3Final,
    _aspect_from_matrix,
    load_references,
)
from .harness import Harness, HarnessRequest, HarnessResult
from .pipeline import DONE, PipelineOrchestrator, StepContext
from .state import load_state, save_state


def next_step(step: str) -> str:
    """STEPS에서 다음 단계. done은 고정점. (STEPS는 step 선언 유도 — 백로그 ④)"""
    idx = STEPS.index(step)
    return STEPS[idx + 1] if idx + 1 < len(STEPS) else DONE


class DesignHarness(Harness):
    # 호환 별칭 — 단일 출처는 design/ 패키지(테스트 표면: DesignHarness.RUBRIC 등).
    RUBRIC = _SCORING_RUBRIC
    NOTICES = NOTICES
    DISCLOSURE_DISPLAY = DISCLOSURE_DISPLAY

    def __init__(self, *, image_provider) -> None:
        self._image_provider = image_provider
        # 오케스트레이터·step 객체는 per-인스턴스(registry 요청 스코프 패턴, 체크리스트 ⑨).
        # step 객체는 턴-가변 상태를 갖지 않는다(전부 ctx로, 체크리스트 ⑩).
        self._orch = PipelineOrchestrator(
            (S0Setup(), S1Rough(), S2aVisual(image_provider),
             S2bCopy(), S2cBrand(), S3Final()),
            studio="design",
            done_text="디자인을 확정했습니다. 검토(review) 단계로 진행할 수 있습니다.",
            done_output="metadata.md",
            save_state=self._save_state)

    def system_prompt(self) -> str:
        return PERSONA

    def _base(self, run_id: str) -> str:
        return f"/{run_id}/design"

    def _load_state(self, store, run_id: str) -> dict:
        st = load_state(store, run_id, "design", default_factory=lambda: {
            "step": "S0", "gate": None, "confirmed": {}, "bypass": {},
            "languages": ["ko"]})
        st.setdefault("gate", None)   # 레거시 run 백필(spec §6)
        st.pop("pending_ask", None)   # 죽은 키 — 라이브 기존 run에서 제거(T1 백로그 ⑤)
        # 진행 중 run이 dict 형태 languages를 영속했더라도 안전하게 정규화(unhashable 방지).
        st["languages"] = normalize_languages(st.get("languages"))
        return st

    def _save_state(self, store, run_id: str, state: dict) -> None:
        save_state(store, run_id, "design", state)

    def handle_turn(self, req: HarnessRequest, *, provider, store) -> HarnessResult:
        state = self._load_state(store, req.run_id)
        # StepContext는 매 턴 메서드 로컬 조립(인스턴스 보관 금지) — cache 신선도 계약(체크리스트 ③).
        ctx = StepContext(req=req, provider=provider, store=store, state=state,
                          base=self._base(req.run_id))
        return self._orch.handle_turn(ctx)

    def _parse_json(self, text: str) -> dict:
        # 테스트 표면 유지 — 구현은 core.parsing 단일본.
        return parse_json_block(text)

    def _load_references(self) -> list[dict]:
        # 테스트 표면 유지 — 구현은 design/steps.py 단일본.
        return load_references()
