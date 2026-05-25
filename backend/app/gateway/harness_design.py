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
import os
import re

import yaml

from ..core.grounding import build_corpus, find_ungrounded
from ..providers.base import Message
from .harness import Harness, HarnessRequest, HarnessResult

STEPS = ("S0", "S1", "S2a", "S2b", "S2c", "S3", "done")

PERSONA = (
    "당신은 금융 마케팅 시니어 아트디렉터입니다. 시각 위계·그리드·여백·CTA 배치·"
    "브랜드 일관성·컴플라이언스 톤에 능하며, 텍스트는 절대 비주얼 픽셀에 굽지 않고 "
    "레이어로 분리합니다. 레이아웃은 구조화 JSON으로만 출력합니다."
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
        if step == "S1":
            return self._s1_rough(req, provider, store, state)
        if step == "S2a":
            return self._s2a_visual(req, provider, store, state)
        if step == "S2b":
            return self._s2b_copy(req, provider, store, state)
        raise NotImplementedError(f"{step} 미구현 (Task 8~11)")

    def _load_references(self) -> list[dict]:
        d = os.path.join(os.path.dirname(__file__), "..", "references", "design")
        out = []
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                with open(os.path.join(d, fn), encoding="utf-8") as f:
                    out.append(json.load(f))
        return out

    def _parse_json(self, text: str) -> dict:
        text = (text or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
        try:
            return json.loads(text)
        except Exception:
            m = re.search(r"\{.*\}", text, re.S)
            return json.loads(m.group(0)) if m else {}

    def _s1_rough(self, req, provider, store, state) -> HarnessResult:
        base = self._base(req.run_id)
        tokens = store.get(f"{base}/design-system/tokens.json")
        refs = self._load_references()
        sys = self.system_prompt() + (
            "\n\n[S1 Rough] 아래 레퍼런스 레이아웃을 참고해 layout_spec(JSON)을 출력하세요. "
            "텍스트는 copy[lang][key]에, 슬롯은 role/bbox/z/copy_key로. "
            'JSON 한 개만: {"reply":"...","layout_spec":{...},"ready":true/false}'
            f"\n[tokens]\n{tokens.content_text if tokens else '{}'}"
            f"\n[references]\n{json.dumps(refs, ensure_ascii=False)}")
        resp = provider.complete([Message("user", req.user_prompt or "러프 시작")],
                                 model=req.provider, system=sys)
        data = self._parse_json(resp.text)
        spec = data.get("layout_spec") or {}
        store.put(f"{base}/rough/layout.spec.json",
                  json.dumps(spec, ensure_ascii=False), source="marker",
                  mime="application/json")
        state["confirmed"]["S1"] = True
        state["step"] = "S2a"
        self._save_state(store, req.run_id, state)
        return HarnessResult(text=data.get("reply", "러프 완성"),
            output_path=f"{base}/rough/layout.spec.json",
            meta={"source": "marker", "step": "S1"},
            events=[{"type": "artifact", "path": f"{base}/rough/layout.spec.json"}])

    def _s2a_visual(self, req, provider, store, state) -> HarnessResult:
        base = self._base(req.run_id)
        spec = self._parse_json(
            (store.get(f"{base}/rough/layout.spec.json") or _empty()).content_text)
        concept = spec.get("visual_concept", "금융 브랜드 추상 배경")
        aspect = spec.get("aspect", "1:1")
        png = self._image_provider.generate_image(concept, aspect=aspect)
        path = f"{base}/design-system/components/visual/v1.png"
        store.put(path, png, source="gemini", mime="image/png",
                  meta={"concept": concept, "aspect": aspect})
        state["confirmed"]["S2a"] = True
        state["step"] = "S2b"
        self._save_state(store, req.run_id, state)
        return HarnessResult(text="비주얼을 생성했습니다.", output_path=path,
            meta={"source": "gemini", "step": "S2a"},
            events=[{"type": "artifact", "path": path}])

    def _s2b_copy(self, req, provider, store, state) -> HarnessResult:
        base = self._base(req.run_id)
        plan = store.get(f"/{req.run_id}/brainstorming/plan.md")
        fm = _frontmatter(plan.content_text if plan else "")
        corpus = build_corpus(fm.get("factsheet") or {})
        sys = self.system_prompt() + (
            "\n\n[S2b 카피·타이포] 헤드라인/바디/CTA를 언어별로 확정하세요. "
            f"factsheet 외 수치 금지. JSON: {{\"copy\":{{lang:{{headline,body,cta}}}}}}"
            f"\n[factsheet]\n{json.dumps(fm.get('factsheet') or {}, ensure_ascii=False)}")
        resp = provider.complete([Message("user", req.user_prompt or "카피 확정")],
                                 model=req.provider, system=sys)
        copy = (self._parse_json(resp.text).get("copy")) or {}
        ungrounded = []
        for lang, fields in copy.items():
            for role in ("headline", "body", "cta"):
                val = (fields or {}).get(role, "")
                ungrounded += find_ungrounded(val, corpus)
                folder = {"headline": "headline", "body": "body", "cta": "cta"}[role]
                store.put(f"{base}/design-system/components/{folder}/{lang}.txt",
                          val, source="marker", mime="text/plain",
                          meta={"lang": lang, "role": role})
        state["confirmed"]["S2b"] = True
        state["step"] = "S2c"
        self._save_state(store, req.run_id, state)
        return HarnessResult(text="카피를 확정했습니다.",
            output_path=f"{base}/design-system/components/headline",
            meta={"source": "marker", "step": "S2b", "ungrounded": sorted(set(ungrounded))},
            events=[{"type": "artifact", "path": f"{base}/design-system/components/headline"}])

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
