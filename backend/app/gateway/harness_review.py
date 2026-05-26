"""ReviewHarness — R0~R3 5-step 핸들러 (DesignHarness 패턴 미러).

상태 단일주인 = /{run}/review/_state.json. 텍스트 액터=handle_turn provider(선택).
비주얼 액터=생성 시 주입된 vision_provider(항상 google/Gemini 멀티모달).

spec: jb-marker/docs/specs/2026-05-26-m5-review-studio-design.md
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

import yaml

from ..core.legal_search import _parse_json, apply_whitelist, load_whitelist, search_and_filter
from ..core.severity import (  # T7: import-only, 사용은 T11/T14
    DISCLOSURE_I18N,
    EXAGGERATION_TOKENS,
    compute_gate,
    detect_exaggeration,
    find_missing_disclosures,
)
from ..providers.base import Message, Provider
from .harness import Harness, HarnessRequest, HarnessResult


def _verdict_id(node: str, clause_or_kind: str, slot: str, lang: str | None) -> str:
    """안정 ID — 동일 finding은 재검토 시 동일 verdict_id (spec §5.3)."""
    key = f"{clause_or_kind}|{slot}|{lang}"
    return f"{node[:5]}_{hashlib.sha1(key.encode()).hexdigest()[:8]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

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

    # ----- step 핸들러 -----
    def _cleanup_review_tree(self, store, run_id: str) -> None:
        """R0 진입 시 stale 산출 전부 삭제(spec §3.7 멱등 재구축).

        legal/·i18n/·revise/·report.md 삭제. _render/·_state.json 보존.
        """
        base = self._base(run_id)
        for prefix in (f"{base}/legal/", f"{base}/i18n/", f"{base}/revise/"):
            nodes = store.list(prefix)
            for n in nodes:
                store.delete(n.path)
        if store.get(f"{base}/report.md"):
            store.delete(f"{base}/report.md")

    def _r0_setup(self, req: HarnessRequest, store, state: dict) -> HarnessResult:
        base = self._base(req.run_id)
        run_id = req.run_id

        # plan.md frontmatter → languages·disclosures
        plan_node = store.get(f"/{run_id}/brainstorming/plan.md")
        fm = _frontmatter(plan_node.content_text if plan_node else "")
        languages = fm.get("languages") or ["ko"]

        # 멱등 cleanup (stale 제거)
        self._cleanup_review_tree(store, run_id)

        # matrix: 언어별 scene/render, 컴포넌트 자산
        matrix: dict = {}
        for lang in languages:
            scene = store.get(f"/{run_id}/design/final/{lang}/main.scene")
            render = store.get(f"{base}/_render/{lang}.png")
            matrix[lang] = {"scene": scene is not None,
                            "render": render is not None}
        components: list[str] = []
        if store.get(f"/{run_id}/design/design-system/components/visual/v1.png"):
            components.append("visual/v1.png")
        matrix["components"] = components

        # state 영속 — 5트리거 flags 모두 초기화
        state.update({
            "step": "R1", "languages": languages, "matrix": matrix,
            "acknowledged": False,
            "live_unavailable": False, "parse_failed": False,
            "vision_failed": False, "step_failed": "",
            "vision_skipped": [], "dropped_findings_count": 0,
            "r2_skipped": "",
        })
        self._save_state(store, run_id, state)
        store.set_step_status(run_id, "review", "in_progress")

        return HarnessResult(
            text=f"검토 매트릭스를 준비했습니다 ({len(languages)}개 언어).",
            output_path=f"{base}/_state.json",
            meta={"source": "marker", "step": "R0", "languages": languages},
            events=[{"type": "artifact", "path": f"{base}/_state.json"}])

    def _persist_verdict(self, store, run_id: str, *, node: str, asset_id: str,
                          lang: str | None, severity: str, location: dict,
                          evidence: str, clause: str | None = None,
                          official_source_url: str | None = None,
                          kind: str | None = None,
                          disclosure: str | None = None) -> str:
        """verdict 봉투 영속 → verdict_id 반환.

        R1(legal)·R2(i18n) 공용. envelope 필수 필드: verdict_id·node·asset_id·
        lang·severity·location·evidence·audit_trace_id·created_at.
        선택: clause·official_source_url·kind·disclosure.
        """
        key = clause if clause else (kind or "")
        slot = location.get("slot", "")
        vid = _verdict_id(node, key, slot, lang or "")
        envelope = {
            "verdict_id": vid, "node": node, "asset_id": asset_id, "lang": lang,
            "severity": severity, "location": location,
            "evidence": evidence,
            "audit_trace_id": str(uuid.uuid4()),
            "created_at": _now_iso(),
        }
        if clause is not None:
            envelope["clause"] = clause
        if official_source_url is not None:
            envelope["official_source_url"] = official_source_url
        if kind is not None:
            envelope["kind"] = kind
        if disclosure is not None:
            envelope["disclosure"] = disclosure
        folder = "legal" if node == "legal" else "i18n"
        prefix = "law_" if node == "legal" else "reason_"
        path = f"{self._base(run_id)}/{folder}/{prefix}{vid.split('_', 1)[1]}/verdict.json"
        store.put(path, json.dumps(envelope, ensure_ascii=False),
                  source="marker", mime="application/json")
        return vid

    def _collect_scene_copy(self, store, run_id: str, languages: list[str]) -> dict:
        """모든 언어 scene의 copy 슬롯 모음."""
        out: dict = {}
        for lang in languages:
            n = store.get(f"/{run_id}/design/final/{lang}/main.scene")
            if not n:
                continue
            try:
                spec = json.loads(n.content_text)
            except Exception:
                spec = {}
            copy = (spec.get("copy") or {}).get(lang) or {}
            out[lang] = copy
        return out

    def _r1_legal(self, req: HarnessRequest, provider, store, state: dict) -> HarnessResult:
        base = self._base(req.run_id)
        languages = state["languages"]

        scene_copy = self._collect_scene_copy(store, req.run_id, languages)
        meta_node = store.get(f"/{req.run_id}/design/metadata.md")
        metadata_md = meta_node.content_text if meta_node else ""
        whitelist = load_whitelist()

        # 호출 1: 텍스트+서칭
        kept, dropped, meta_flags = search_and_filter(
            provider, scene_copy, metadata_md, whitelist)
        if meta_flags.get("live_unavailable"):
            state["live_unavailable"] = True
        if meta_flags.get("parse_failed"):
            state["parse_failed"] = True
        state["dropped_findings_count"] += dropped
        for f in kept:
            loc = f.get("location", {}) or {}
            f_lang = loc.get("lang")
            self._persist_verdict(
                store, req.run_id, node="legal",
                asset_id=f"design/final/{f_lang or ''}/main.scene",
                lang=f_lang,
                severity=f.get("severity", "warning"),
                location=loc,
                evidence=f.get("evidence", ""),
                clause=f.get("clause"),
                official_source_url=f.get("official_source_url"))

        # 호출 2: 컴포넌트 단독 비전 (v1.png — text-free 계약·오해유발·상표침해)
        v1 = store.get(f"/{req.run_id}/design/design-system/components/visual/v1.png")
        if v1 is None:
            state["vision_skipped"].append("visual/v1.png")
        else:
            vision_prompt = (
                "이 이미지는 금융 마케팅 캠페인용 AI 생성 비주얼입니다(텍스트-free 계약). "
                "다음을 평가하세요: ① 이미지에 우발 텍스트가 박혔는지(계약 위반) "
                "② 수익 보장·무위험 등 오해 유발 비주얼 ③ 상표·로고 침해. "
                "공식 법령 출처(law.go.kr 등)만 인용. "
                'JSON: {"findings":[{"location":{"slot":"visual","lang":null},'
                '"clause":"...","official_source_url":"https://law.go.kr/...",'
                '"severity":"critical|warning","evidence":"..."}, ...]}'
            )
            try:
                img_bytes = v1.blob if v1.blob else (v1.content_text or "").encode("utf-8")
                vresp = self._vision_provider.review_image(
                    img_bytes, vision_prompt, mime="image/png")
                vdata = _parse_json(vresp.text)
                vfindings = vdata.get("findings") or []
                vkept, vdropped = apply_whitelist(vfindings, whitelist)
                state["dropped_findings_count"] += vdropped
                for f in vkept:
                    self._persist_verdict(
                        store, req.run_id, node="legal",
                        asset_id="design/design-system/components/visual/v1.png",
                        lang=None,
                        severity=f.get("severity", "warning"),
                        location={"slot": "visual", "lang": None},
                        evidence=f.get("evidence", ""),
                        clause=f.get("clause"),
                        official_source_url=f.get("official_source_url"))
            except Exception:
                state["vision_failed"] = True
                state["vision_skipped"].append("visual/v1.png")

        # 호출 3: 언어별 합성 비전 (_render/{lang}.png — 고지 가독성·전체 메시지)
        for lang in languages:
            render = store.get(f"{base}/_render/{lang}.png")
            if render is None:
                state["vision_skipped"].append(f"composite/{lang}")
                continue
            composite_prompt = (
                f"이 이미지는 {lang} 언어 금융 마케팅 캠페인의 합성 렌더(텍스트+비주얼)입니다. "
                "다음을 평가하세요: ① 필수고지의 가독성·배치 ② 이미지+텍스트 결합이 만드는 "
                "전체 메시지의 위법성(수익 보장 단정·오인 유발). "
                "공식 법령 출처(law.go.kr 등)만 인용. "
                'JSON: {"findings":[{"location":{"slot":"composite","lang":"' + lang + '"},'
                '"clause":"...","official_source_url":"https://law.go.kr/...",'
                '"severity":"critical|warning","evidence":"..."}, ...]}'
            )
            try:
                render_bytes = render.blob if render.blob else (render.content_text or "").encode("utf-8")
                cresp = self._vision_provider.review_image(
                    render_bytes, composite_prompt, mime="image/png")
                cdata = _parse_json(cresp.text)
                cfindings = cdata.get("findings") or []
                ckept, cdropped = apply_whitelist(cfindings, whitelist)
                state["dropped_findings_count"] += cdropped
                for f in ckept:
                    self._persist_verdict(
                        store, req.run_id, node="legal",
                        asset_id=f"review/_render/{lang}.png",
                        lang=lang,
                        severity=f.get("severity", "warning"),
                        location={"slot": "composite", "lang": lang},
                        evidence=f.get("evidence", ""),
                        clause=f.get("clause"),
                        official_source_url=f.get("official_source_url"))
            except Exception:
                state["vision_failed"] = True
                state["vision_skipped"].append(f"composite/{lang}")

        state["step"] = "R2"
        self._save_state(store, req.run_id, state)
        return HarnessResult(
            text=f"R1 법률 검토 완료 (텍스트 {len(kept)}건).",
            output_path=f"{base}/legal/",
            meta={"source": "marker", "step": "R1",
                  "findings_text": len(kept), "dropped": dropped},
            events=[{"type": "artifact", "path": f"{base}/legal/"}])

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
