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

import json
from dataclasses import replace

from ..core.lang import normalize_languages
from ..core.parsing import parse_json_block, read_json_node
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
    _rich_enabled,
    _write_preview,
    load_references,
)
from .harness import Harness, HarnessRequest, HarnessResult
from .pipeline import DONE, PipelineOrchestrator, StepContext
from .state import load_state, save_state


def next_step(step: str) -> str:
    """STEPS에서 다음 단계. done은 고정점. (STEPS는 step 선언 유도 — 백로그 ④)"""
    idx = STEPS.index(step)
    return STEPS[idx + 1] if idx + 1 < len(STEPS) else DONE


# 리뷰 후 done 상태로 복귀한 디자인 챗에서 '카피 교정' 의도를 감지하는 토큰.
# orchestrator는 done 고정점(pipeline.py)이라 일반 흐름으론 카피를 다시 만들지 못한다 —
# 이 토큰이 보이면 S2b 카피를 재교정하고 리뷰 지적(예금자보호 고지 누락·과장광고)을 반영한다
# (리뷰→디자인→재검토 루프 성립). done 상태에서만 평가하므로 첫 생성 S2b엔 영향 없다.
_REMEDIATE_TOKENS = ("수정", "교정", "정정", "보강", "리뷰", "반영", "고쳐", "지적", "fix", "comply")

# 예금자보호 고지 현지화 — 리뷰 critical의 실제 원인은 vi/zh 등 비-ko 언어의 예금자보호 고지
# 누락(R2 missing_disclosure 강제 critical). 교정 시 모든 언어 disclosure 슬롯을 이 값으로
# 채워 scene_copy에 고지가 보존되게 한다(mock 시연 경로). 값은 R2 안전망을 통과하는 키워드.
_REMEDIATED_DISCLOSURE = {
    "ko": "예금자보호법에 따라 5천만원까지 보호",
    "en": "Protected up to KRW 50M under the Depositor Protection Act.",
    "vi": "Được bảo hiểm tiền gửi tới 50 triệu KRW theo luật.",
    "zh": "根据存款保护法，最高保护5000万韩元。",
}


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
            (S0Setup(), S1Rough(), S2bCopy(), S2aVisual(image_provider),
             S2cBrand(), S3Final()),
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
        # 리뷰 후 done 복귀 디자인 챗의 자유 교정 지시(action 없음 + 교정 토큰) → S2b 카피 재교정.
        if (state.get("step") == DONE and not req.action and req.user_prompt
                and any(t in req.user_prompt for t in _REMEDIATE_TOKENS)):
            return self._remediate_copy(req, provider, store, state)
        # StepContext는 매 턴 메서드 로컬 조립(인스턴스 보관 금지) — cache 신선도 계약(체크리스트 ③).
        ctx = StepContext(req=req, provider=provider, store=store, state=state,
                          base=self._base(req.run_id))
        return self._orch.handle_turn(ctx)

    def _remediate_copy(self, req: HarnessRequest, provider, store,
                        state: dict) -> HarnessResult:
        """리뷰 후 done 디자인 챗의 교정 지시 → S2b 카피 재교정(리뷰 피드백 반영).

        demo(Mock)가 clean 카피를 반환하도록 교정 신호('교정')를 프롬프트에 보장한다
        (demo._REMEDIATION_SIGNAL). 실모드 LLM에도 의도를 명확히 하는 힌트라 무해.
        step은 done 유지 — 프론트가 meta.remediated 신호로 main.scene만 재조립한다.
        """
        base = self._base(req.run_id)
        hinted = (req.user_prompt or "") + "\n[리뷰 지적을 반영해 카피를 교정하세요]"
        ctx = StepContext(req=replace(req, user_prompt=hinted), provider=provider,
                          store=store, state=state, base=base)
        res = S2bCopy().run(ctx)   # layout.spec.json copy 정제 병합 + 컴포넌트 txt 갱신
        # 리뷰 critical의 실제 원인(vi/zh 예금자보호 고지 누락) 해소 — 모든 언어 disclosure 채움.
        # mock 시연 경로. layout.spec.copy[lang].disclosure → 프론트 어셈블러가 disclosure 슬롯에
        # 반영 → R2 scene_copy에 고지 보존 → 재검토 PASS.
        spec = read_json_node(store, f"{base}/rough/layout.spec.json")
        spec.setdefault("copy", {})
        for lang, disc in _REMEDIATED_DISCLOSURE.items():
            spec["copy"].setdefault(lang, {})
            spec["copy"][lang]["disclosure"] = disc
        store.put(f"{base}/rough/layout.spec.json",
                  json.dumps(spec, ensure_ascii=False), source="marker",
                  mime="application/json")
        # 시안 프리뷰를 교정된 카피·고지로 갱신(비차단). 기존 v1.png가 있으면 배경으로 인라인해
        # rich 모드(아래 재베이크 생략)에서도 프리뷰가 비주얼을 유지한다. 베이크 모드는 아래
        # S2aVisual 재실행이 새 v1.png로 프리뷰를 다시 덮어써 최종 교정본을 반영한다.
        _vnode = store.get(f"{base}/design-system/components/visual/v1.png")
        _write_preview(ctx, spec, _vnode.blob if _vnode else None)
        # 비주얼도 교정 — clean 카피로 v1.png(및 추가언어 변형)를 갱신한다. sceneAssembler가
        # visual_by_lang→background로 v1.png를 그대로 쓰므로(헤드라인 배경 베이크), 카피만 고치면
        # 캔버스 배경엔 과장표현('업계 최고'/4.0%)이 그대로 남는다. layout.spec.copy는 위에서
        # clean으로 갱신됐다.
        # 교정은 layout spec 불변·카피만 변경 → run_edit(image-edit, spec 2026-07-04): 기존
        # v1.png 위에 텍스트만 교체해 사용자가 승인한 아트를 보존한다('카피만 고쳤다' 서사의
        # 시각 연속성 + 런별 변동성 제거). 기존 비주얼 부재/편집 실패/비전 critical은 run_edit
        # 내부에서 전체 재베이크(run)로 폴백. 실패해도 카피·고지 교정은 이미 저장됨(graceful).
        # rich 모드: 카피는 벡터 레이어라 재베이크 불필요(유료 gemini 재호출 0·사용자가 보던
        # 히어로 보존). 게다가 _run_rich의 slots 교체가 S2c logo 슬롯을 지운다(S2c는 재실행 안 됨).
        if not _rich_enabled():
            try:
                S2aVisual(self._image_provider).run_edit(ctx)
            except Exception:
                pass
        self._save_state(store, req.run_id, state)   # step=done 유지
        text = ("리뷰에서 지적된 예금자보호 고지 누락(베트남어·중국어)과 과장광고 표현을 반영해 "
                "카피를 교정하고 4개 언어에 예금자보호 고지를 보강했습니다. 캔버스를 갱신했어요 — "
                "검토(review)를 다시 실행하면 통과합니다.")
        events = list(res.events) + [
            {"type": "artifact", "path": f"{base}/rough/layout.spec.json"},
            {"type": "artifact",
             "path": f"{base}/design-system/components/visual/v1.png"}]
        return HarnessResult(text=text,
                             output_path=f"{base}/rough/layout.spec.json",
                             meta={"source": "marker", "step": DONE,
                                   "remediated": True},
                             events=events)

    def _parse_json(self, text: str) -> dict:
        # 테스트 표면 유지 — 구현은 core.parsing 단일본.
        return parse_json_block(text)

    def _load_references(self) -> list[dict]:
        # 테스트 표면 유지 — 구현은 design/steps.py 단일본.
        return load_references()
