"""Video 파이프라인 단계 — PipelineStep 구현 (design/steps.py 미러, spec §3).

V2aFootage만 매체 액터(video_provider)를 생성자 주입받고, 나머지는 무상태.
V2b/V2c는 design S2b/S2c의 매체-비의존 로직 복제(공유 추출은 후속 — spec §9).
"""
from __future__ import annotations

import json

from ...core.grounding import build_corpus, find_ungrounded
from ...core.lang import normalize_languages
from ...core.parsing import parse_frontmatter as _frontmatter, parse_json_block, read_json_node
from ...providers.base import Message
from ..critic import CriticVerdict
from ..design.steps import DISCLOSURE_DISPLAY, NOTICES  # 법령 표시문 데이터 재사용(단일 소스)
from ..harness import HarnessResult
from ..pipeline import DONE, GateCheck, PipelineStep, StepContext
from ..prompt import PromptSpec
from .prompts import PERSONA, V1_INSTR, V2B_INSTR
from .scoring import RUBRIC, evaluate_timing, run_critic, timing_summary

# V3 채점 raw의 턴 캐시 키 — V3Final.run이 기록, critic_gate가 재사용(design 백로그 ② 미러).
V3_CRITIC_CACHE = "v3_critic"


def _visual_gate(raw: dict) -> GateCheck:
    env = CriticVerdict.from_scores(raw)
    return GateCheck(passed=env.passed, critic=env.to_dict())


class V0Setup(PipelineStep):
    """plan.md frontmatter → video tokens + material_matrix + languages (S0Setup 미러)."""

    name = "V0"
    gated = False

    def run(self, ctx: StepContext) -> HarnessResult:
        base = ctx.base
        plan = ctx.store.get(f"/{ctx.req.run_id}/brainstorming/plan.md")
        fm = _frontmatter(plan.content_text if plan else "")
        vd = fm.get("video_direction") or {}
        matrix = fm.get("material_matrix", [])
        tokens = {
            "duration_sec": vd.get("duration_sec", 15),
            "aspect": vd.get("aspect", "9:16"),
            "fps": vd.get("fps", 30),
            "pacing": vd.get("pacing", "medium"),
            "mood": vd.get("mood"),
            "palette": vd.get("palette") or [],
            "font": vd.get("font"),
            "music": vd.get("music"),
            "voiceover": bool(vd.get("voiceover", False)),
        }
        ctx.store.put(f"{base}/design-system/tokens.json",
                      json.dumps(tokens, ensure_ascii=False), source="marker",
                      mime="application/json")
        ctx.store.put(f"{base}/_material_matrix.json",
                      json.dumps(matrix, ensure_ascii=False), source="marker",
                      mime="application/json")
        ctx.state["languages"] = normalize_languages(fm.get("languages"))
        return HarnessResult(
            text="영상 토큰을 확정했습니다. 콘티(Storyboard) 단계로 진행합니다.",
            output_path=f"{base}/design-system/tokens.json",
            meta={"source": "marker", "step": self.name},
            events=[{"type": "artifact", "path": f"{base}/design-system/tokens.json"}])


class V1Storyboard(PipelineStep):
    """토큰+비트 → storyboard.spec.json (S1Rough 미러). 시각 critic 게이트(비캐시)."""

    name = "V1"
    gated = True

    def run(self, ctx: StepContext) -> HarnessResult:
        base = ctx.base
        tokens = ctx.store.get(f"{base}/design-system/tokens.json")
        plan = ctx.store.get(f"/{ctx.req.run_id}/brainstorming/plan.md")
        fm = _frontmatter(plan.content_text if plan else "")
        beats = {"scene_beats": fm.get("scene_beats"),
                 "footage_concept": fm.get("footage_concept")}
        pspec = PromptSpec(
            persona=PERSONA,
            constraints=[V1_INSTR],
            references=[f"\n[tokens]\n{tokens.content_text if tokens else '{}'}",
                        f"\n[beats]\n{json.dumps(beats, ensure_ascii=False)}"],
            studio="video", step=self.name)
        resp = ctx.provider.complete([Message("user", ctx.req.user_prompt or "콘티 시작")],
                                     system=pspec.assemble(), meta=pspec.meta)
        data = parse_json_block(resp.text)
        spec = data.get("storyboard") or {}
        ctx.store.put(f"{base}/storyboard/storyboard.spec.json",
                      json.dumps(spec, ensure_ascii=False), source="marker",
                      mime="application/json")
        return HarnessResult(text=data.get("reply", "콘티 완성"),
            output_path=f"{base}/storyboard/storyboard.spec.json",
            meta={"source": "marker", "step": self.name},
            events=[{"type": "artifact", "path": f"{base}/storyboard/storyboard.spec.json"}])

    def critic_gate(self, ctx: StepContext) -> GateCheck:
        spec = read_json_node(ctx.store, f"{ctx.base}/storyboard/storyboard.spec.json")
        return _visual_gate(run_critic(ctx.provider, spec))


class V2aFootage(PipelineStep):
    """샷별 배경 footage 생성 — 매체 액터 생성자 주입 (S2aVisual 미러). critic 없음."""

    name = "V2a"
    gated = True

    def __init__(self, video_provider) -> None:
        self._video_provider = video_provider   # 턴-불변 의존성

    def run(self, ctx: StepContext) -> HarnessResult:
        base = ctx.base
        spec = read_json_node(ctx.store, f"{base}/storyboard/storyboard.spec.json")
        aspect = spec.get("aspect", "9:16")
        duration = int(spec.get("duration_sec", 15))
        shots = spec.get("shots") or [{"id": "s1", "footage_prompt": "금융 브랜드 추상 배경"}]
        any_fallback = False
        for shot in shots:
            sid = shot.get("id", "s1")
            prompt = shot.get("footage_prompt", "금융 브랜드 추상 배경")
            try:
                clip = self._video_provider.generate_video(
                    prompt, aspect=aspect, duration_sec=duration)
                mime, fallback = "video/mp4", False
            except Exception:
                from ...providers import demo_fixtures as F
                clip = F.load_poster_bg()   # still → 프론트가 모션 부여
                mime, fallback = "image/png", True
            any_fallback = any_fallback or fallback
            ctx.store.put(f"{base}/design-system/components/footage/clip_{sid}.mp4",
                          clip, source="veo", mime=mime,
                          meta={"shot": sid, "footage_fallback": fallback})
        text = ("배경 footage를 생성했습니다." if not any_fallback else
                "실 영상 생성에 실패해 대체 배경(still)을 사용했습니다. "
                "실 footage는 GOOGLE_API_KEY 설정이 필요합니다.")
        return HarnessResult(text=text,
            output_path=f"{base}/design-system/components/footage",
            meta={"source": "veo", "step": self.name, "footage_fallback": any_fallback},
            events=[{"type": "artifact",
                     "path": f"{base}/design-system/components/footage"}])
