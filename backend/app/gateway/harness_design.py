"""DesignHarness — plan.md → S0~S3 디자인 파이프라인(stateless step 핸들러).

상태 단일주인 = /{run}/design/_state.json. 텍스트 액터=handle_turn provider(선택),
비주얼 액터=생성 시 주입된 image_provider(항상 google/Nano Banana).

BrainstormingHarness의 상태 I/O 패턴을 미러:
- _load_state/_save_state: /{run}/design/_state.json 단일 소스
- handle_turn(self, req, *, provider, store): step 디스패치
- HarnessResult(text=, output_path=, meta=, events=)
"""
from __future__ import annotations

import json

import yaml

from .harness import Harness, HarnessRequest, HarnessResult

STEPS = ("S0", "S1", "S2a", "S2b", "S2c", "S3", "done")

PERSONA = (
    "당신은 금융 마케팅 시니어 아트디렉터입니다. 시각 위계·그리드·여백·CTA 배치·"
    "브랜드 일관성·컴플라이언스 톤에 능하며, 텍스트는 절대 비주얼 픽셀에 굽지 않고 "
    "레이어로 분리합니다. 레이아웃은 구조화 JSON으로만 출력합니다."
)


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


class DesignHarness(Harness):
    def __init__(self, *, image_provider) -> None:
        self._image_provider = image_provider

    def system_prompt(self) -> str:
        return PERSONA

    def _base(self, run_id: str) -> str:
        return f"/{run_id}/design"

    def _load_state(self, store, run_id: str) -> dict:
        n = store.get(f"{self._base(run_id)}/_state.json")
        if n and n.content_text:
            return json.loads(n.content_text)
        return {"step": "S0", "confirmed": {}, "bypass": {}, "languages": ["ko"],
                "pending_ask": None}

    def _save_state(self, store, run_id: str, state: dict) -> None:
        store.put(f"{self._base(run_id)}/_state.json",
                  json.dumps(state, ensure_ascii=False),
                  source="marker", mime="application/json")

    def handle_turn(self, req: HarnessRequest, *, provider, store) -> HarnessResult:
        state = self._load_state(store, req.run_id)
        step = state["step"]
        if step == "S0":
            return self._s0_setup(req, store, state)
        return self._dispatch(step, req, provider, store, state)

    def _dispatch(self, step, req, provider, store, state) -> HarnessResult:
        raise NotImplementedError(f"{step} 미구현 (Task 6~11)")

    def _s0_setup(self, req: HarnessRequest, store, state: dict) -> HarnessResult:
        base = self._base(req.run_id)
        plan = store.get(f"/{req.run_id}/brainstorming/plan.md")
        fm = _frontmatter(plan.content_text if plan else "")
        cd = fm.get("creative_direction") or {}
        tokens = {"palette": cd.get("palette", []), "font": cd.get("font"),
                  "grid": cd.get("grid"), "aspect": cd.get("aspect", "1:1")}
        store.put(f"{base}/design-system/tokens.json",
                  json.dumps(tokens, ensure_ascii=False), source="marker",
                  mime="application/json")
        store.put(f"{base}/_material_matrix.json",
                  json.dumps(fm.get("material_matrix", []), ensure_ascii=False),
                  source="marker", mime="application/json")
        state["languages"] = fm.get("languages", ["ko"])
        state["confirmed"]["S0"] = True
        state["step"] = "S1"
        self._save_state(store, req.run_id, state)
        return HarnessResult(
            text="디자인 토큰을 확정했습니다. Rough 단계로 진행합니다.",
            output_path=f"{base}/design-system/tokens.json",
            meta={"source": "marker", "step": "S0"},
            events=[{"type": "artifact", "path": f"{base}/design-system/tokens.json"}])
