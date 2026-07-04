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

from ..core.lang import normalize_languages
from ..core.legal_search import apply_whitelist, load_whitelist, search_and_filter
from ..core.parsing import parse_frontmatter as _frontmatter, parse_json_block as _parse_json
from ..core.severity import (  # T7: import-only, 사용은 T11/T14
    DISCLOSURE_I18N,
    EXAGGERATION_TOKENS,
    compute_gate,
    detect_exaggeration,
    find_missing_disclosures,
)
from ..core.visual_rules import evaluate_visual_compliance
from ..providers.base import Message, Provider
from ..providers.demo_fixtures import HIGHLIGHT_BBOX_FIXTURES
from .harness import GateEnvelope, Harness, HarnessRequest, HarnessResult
from .prompt import PromptSpec
from .review_highlight import resolve_location
from .state import load_state, save_state
from .uploads import list_upload_images


def _verdict_id(node: str, clause_or_kind: str, slot: str, lang: str | None) -> str:
    """안정 ID — 동일 finding은 재검토 시 동일 verdict_id (spec §5.3)."""
    key = f"{clause_or_kind}|{slot}|{lang}"
    return f"{node[:5]}_{hashlib.sha1(key.encode()).hexdigest()[:8]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uploaded_location(uname: str, finding: dict) -> dict:
    """업로드 verdict location — slot에 파일명(verdict_id 유일성), finding의 bbox 있으면 보존.

    비전/mock finding이 location.bbox를 실어 오면 하이라이트로 이어진다(없으면 카드만).
    """
    loc = {"slot": f"uploaded:{uname}", "lang": None}
    bbox = (finding.get("location") or {}).get("bbox")
    if bbox:
        loc["bbox"] = bbox
    return loc


def _actions_for(status: str) -> list[str]:
    """게이트 status별 허용 후속 액션 (spec §4.2). 프론트 버튼 노출 계약."""
    if status == "WARN":
        return ["ack", "regenerate", "restart"]
    if status == "BLOCKED":
        return ["regenerate", "restart"]
    return []


def _controversy_categories() -> frozenset:
    """블랙리스트 category 집합 — 업로드 심의 finding의 논란/법률 라우팅 단일 기준.

    ControversyCard.CATEGORY_KR와 동일 계약(other_sensitive·community_* 등). 업로드
    finding이 이 category를 달면 법률(§clause) 아닌 논란(RC)으로 취급해 controversy 노드로.
    """
    from ..core.controversy_rules import load_blacklist
    return frozenset(e.get("category", "") for e in load_blacklist() if e.get("category"))


STEPS = ("R0", "R1", "R2", "RC", "R3", "done")

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
PERSONA_RC = (
    "당신은 한국 시장의 브랜드 평판·사회 논란 리스크 검토관입니다. "
    "주어진 마케팅 카피·맥락이 사회적 물의·논란을 부를 수 있는지, 제공된 블랙리스트 카테고리에 "
    "근거해 판정합니다. 정치적 옳고 그름을 판단하지 말고, '이 요소가 특정 논란과 연관되어 "
    "의도와 무관하게 오해·물의를 부를 수 있다'는 평판 리스크만 중립적으로, 근거와 함께 표면화하세요. "
    "특히 단독으로는 무해하나 결합 시 위험한 조합(예: 참사 날짜 × 경솔한 모티프)에 주의하세요. "
    'JSON 한 개만: {"findings":[{"location":{"slot":"controversy","lang":"ko|null"},'
    '"category":"...","severity":"critical|warning","evidence":"...","source":"..."}, ...]} '
    "논란 소지 없으면 findings=[]를 반환하세요."
)


class ReviewHarness(Harness):
    def __init__(self, *, vision_provider: Provider) -> None:
        self._vision_provider = vision_provider

    def _base(self, run_id: str) -> str:
        return f"/{run_id}/review"

    def _load_state(self, store, run_id: str) -> dict:
        st = load_state(store, run_id, "review", default_factory=lambda: {
            "step": "R0", "languages": ["ko"], "matrix": {},
            "bypass": {}, "acknowledged": False, "last_run_at": None,
            "live_unavailable": False, "parse_failed": False,
            "vision_failed": False, "step_failed": "",
            "vision_skipped": [], "dropped_findings_count": 0,
            "r2_skipped": "",
        })
        # 진행 중 run이 dict 형태 languages를 영속했더라도 안전하게 정규화(unhashable 방지).
        st["languages"] = normalize_languages(st.get("languages"))
        return st

    def _save_state(self, store, run_id: str, state: dict) -> None:
        save_state(store, run_id, "review", state)

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
        if step == "RC":
            return self._rc_controversy(req, provider, store, state)
        if step == "R3":
            return self._r3_reconcile(req, provider, store, state)
        raise NotImplementedError(f"{step} 미구현 (알 수 없는 step)")

    # ----- step 핸들러 -----
    def _cleanup_review_tree(self, store, run_id: str) -> None:
        """R0 진입 시 stale 산출 전부 삭제(spec §3.7 멱등 재구축).

        legal/·i18n/·revise/·report.md 삭제. _render/·_state.json 보존.
        """
        base = self._base(run_id)
        for prefix in (f"{base}/legal/", f"{base}/i18n/",
                       f"{base}/controversy/", f"{base}/revise/"):
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
        # 실 LLM은 languages를 객체 리스트로 쓸 수 있어 문자열 코드로 정규화(경로/matrix 키 안전).
        languages = normalize_languages(fm.get("languages"))

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
        matrix["uploads"] = [p.rsplit("/", 1)[-1]
                             for p in list_upload_images(store, run_id, "review")]

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
                          disclosure: str | None = None,
                          identity: str | None = None) -> str:
        """verdict 봉투 영속 → verdict_id 반환.

        R1(legal)·R2(i18n)·RC(controversy) 공용. envelope 필수 필드: verdict_id·node·
        asset_id·lang·severity·location·evidence·audit_trace_id·created_at.
        선택: clause·official_source_url·kind·disclosure.

        identity: verdict_id 유도용 명시 키(RC 논란 전용). controversy는 clause가 없고
        slot이 상수 "controversy"라 (category, lang)만으로는 같은 카테고리·언어의 서로 다른
        finding이 동일 verdict 경로로 충돌해 나중 것이 앞 것을 덮어쓴다(critical 강등). 블랙리스트
        entry의 고유 id를 identity로 넘겨 finding별 고유 경로를 보장한다. 미전달(legal/i18n)이면
        기존 clause/kind 유도라 동작 byte-identical.
        """
        key = identity or clause or (kind or "")
        slot = location.get("slot", "")
        # 하이라이트 좌표 부착(비파괴) — layout.spec + authored fixture로 image·bbox 해결.
        _ls = store.get(f"/{run_id}/design/rough/layout.spec.json")
        _layout = {}
        if _ls and _ls.content_text:
            try:
                _layout = json.loads(_ls.content_text)
            except Exception:
                _layout = {}
        location = resolve_location(location, asset_id=asset_id, lang=lang,
                                    layout_spec=_layout, fixtures=HIGHLIGHT_BBOX_FIXTURES)
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
        folder = {"legal": "legal", "i18n": "i18n",
                  "controversy": "controversy"}.get(node, "i18n")
        prefix = {"legal": "law_", "i18n": "reason_",
                  "controversy": "risk_"}.get(node, "reason_")
        path = f"{self._base(run_id)}/{folder}/{prefix}{vid.split('_', 1)[1]}/verdict.json"
        store.put(path, json.dumps(envelope, ensure_ascii=False),
                  source="marker", mime="application/json")
        return vid

    def _collect_scene_copy(self, store, run_id: str, languages: list[str]) -> dict:
        """모든 언어 scene의 copy 슬롯 모음 — layout.spec(베이크 카피) + main.scene(씬 상태) 병합.

        원-레이어 구조에선 헤드라인/바디/CTA가 배경 v1.png에 **베이크**되어 main.scene의
        textbox엔 disclosure만 남는다. 이 textbox만 보면 R1 법률 검토가 헤드라인의 과장광고·
        금리 불일치('업계 최고'/4.0%)를 못 봐 무탐이 된다. 따라서 백엔드 layout.spec.json[copy]
        (베이크된 헤드라인/바디/CTA 보유)를 **베이스**로 깔고, main.scene의 실제 씬 상태
        (사용자 편집·disclosure 등)를 **오버레이**해 병합한다 → R1이 헤드라인 카피를, R2가
        disclosure를 모두 본다. main.scene이 없으면 layout.spec만, layout.spec이 없으면 scene만.
        """
        out: dict = {}
        for lang in languages:
            # 베이스: 베이크된 헤드라인/바디/CTA(R1 과장광고·금리 검사용).
            layout_copy: dict = {}
            ls = store.get(f"/{run_id}/design/rough/layout.spec.json")
            if ls:
                try:
                    layout_copy = (json.loads(ls.content_text).get("copy") or {}).get(lang) or {}
                except Exception:
                    layout_copy = {}
            # 오버레이: main.scene의 실제 씬 상태(사용자 편집·disclosure) — 있으면 우선.
            scene: dict = {}
            n = store.get(f"/{run_id}/design/final/{lang}/main.scene")
            if n:
                try:
                    spec = json.loads(n.content_text)
                except Exception:
                    spec = {}
                scene = (spec.get("copy") or {}).get(lang) or {}
                if not scene:
                    scene = {o.get("role"): o.get("text", "")
                             for o in spec.get("objects", [])
                             if str(o.get("type", "")).lower() == "textbox" and o.get("role")}
            # 병합: 베이크 카피 위에 씬 상태를 덮어쓴다(빈 값은 베이스 보존).
            out[lang] = {**layout_copy, **{k: v for k, v in scene.items() if v}}
        return out

    def _r1_legal(self, req: HarnessRequest, provider, store, state: dict) -> HarnessResult:
        base = self._base(req.run_id)
        languages = state["languages"]

        scene_copy = self._collect_scene_copy(store, req.run_id, languages)
        meta_node = store.get(f"/{req.run_id}/design/metadata.md")
        metadata_md = meta_node.content_text if meta_node else ""
        whitelist = load_whitelist()

        # 호출 0(결정론): 시각 적법성 룰 — layout.spec의 시각 메타데이터(글자크기·대비·고지)를
        # 비전 LLM 무관하게 검사(core/visual_rules). findings는 legal verdict로 영속돼 게이트 합류.
        visual_n = store.get(f"/{req.run_id}/design/rough/layout.spec.json")
        if visual_n:
            try:
                vspec = json.loads(visual_n.content_text)
            except Exception:
                vspec = {}
            for f in evaluate_visual_compliance(vspec):
                self._persist_verdict(
                    store, req.run_id, node="legal",
                    asset_id="design/rough/layout.spec.json", lang=None,
                    severity=f.get("severity", "warning"),
                    location={"slot": f.get("slot", "visual"), "lang": None},
                    evidence=f.get("evidence", ""),
                    clause=f.get("clause"),
                    official_source_url=f.get("official_source_url"),
                    kind="visual")

        # 호출 1: 텍스트+서칭 — meta 명시 신호는 하네스가 만든다(legal_search는 패스스루)
        kept, dropped, meta_flags = search_and_filter(
            provider, scene_copy, metadata_md, whitelist,
            meta={"studio": "review", "step": "R1"})
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

        # 호출 4: 사용자 업로드 소재 심의(있을 때만 — 가산적, mock 계약 불변).
        # 외부/기존 포스터를 같은 법률 기준으로 심의해 verdict → 게이트에 합류시킨다.
        for upath in list_upload_images(store, req.run_id, "review"):
            uname = upath.rsplit("/", 1)[-1]
            unode = store.get(upath)
            if unode is None:
                state["vision_skipped"].append(f"uploads/{uname}")
                continue
            uprompt = (
                f"[uploaded-audit] file={uname}\n"
                "이 이미지는 사용자가 심의를 위해 업로드한 마케팅 소재입니다. "
                "다음을 평가하세요: ① 과장·단정(수익 보장 등) 표현 ② 필수고지 누락 "
                "③ 오해 유발 비주얼·사회적 논란 소지 ④ 상표·저작권 침해 신호. "
                "공식 법령 출처(law.go.kr 등)만 인용. "
                "bbox는 위반 문구가 이미지에서 차지하는 정규화 위치(좌상단 x·y, 폭 w·높이 h, 0~1). "
                'JSON: {"findings":[{"location":{"slot":"uploaded","lang":null,'
                '"bbox":{"x":0.0,"y":0.0,"w":0.0,"h":0.0}},'
                '"clause":"...","official_source_url":"https://law.go.kr/...",'
                '"severity":"critical|warning","evidence":"..."}, ...]}'
            )
            try:
                ubytes = unode.blob if unode.blob else (unode.content_text or "").encode("utf-8")
                uresp = self._vision_provider.review_image(
                    ubytes, uprompt, mime=unode.mime or "image/png")
                udata = _parse_json(uresp.text)
                raw = udata.get("findings") or []
                # 논란(RC) 카테고리 finding은 법률 도메인 화이트리스트 비대상(RC 경로 2·3과
                # 동일 — 논란은 법령 인용이 아니라 평판 리스크) → controversy 노드로 직접
                # 영속해 ControversyCard에 합류. 나머지는 종전대로 법률 화이트리스트(공식
                # 법령 출처만) 통과 후 legal 노드. 업로드 욱일기 포스터 시연이 대표 경로.
                cx_cats = _controversy_categories()
                cx_findings = [f for f in raw if f.get("category") in cx_cats]
                ukept, udropped = apply_whitelist(
                    [f for f in raw if f.get("category") not in cx_cats], whitelist)
                state["dropped_findings_count"] += udropped
                for f in ukept:
                    self._persist_verdict(
                        store, req.run_id, node="legal",
                        asset_id=f"review/uploads/{uname}", lang=None,
                        severity=f.get("severity", "warning"),
                        # slot에 파일명 포함 + finding bbox 보존(하이라이트)
                        location=_uploaded_location(uname, f),
                        evidence=f.get("evidence", ""),
                        clause=f.get("clause"),
                        official_source_url=f.get("official_source_url"),
                        kind="uploaded")
                for f in cx_findings:
                    self._persist_verdict(
                        store, req.run_id, node="controversy",
                        asset_id=f"review/uploads/{uname}", lang=None,
                        severity=f.get("severity", "warning"),
                        # legal 루프와 동일 — slot에 파일명 + finding bbox 보존(라이브 하이라이트)
                        location=_uploaded_location(uname, f),
                        evidence=f.get("evidence", ""),
                        official_source_url=f.get("official_source_url"),
                        kind=f.get("category"), identity=f.get("id"))
            except Exception:
                state["vision_failed"] = True
                state["vision_skipped"].append(f"uploads/{uname}")

        state["step"] = "R2"
        self._save_state(store, req.run_id, state)
        return HarnessResult(
            text=f"R1 법률 검토 완료 (텍스트 {len(kept)}건).",
            output_path=f"{base}/legal/",
            meta={"source": "marker", "step": "R1",
                  "findings_text": len(kept), "dropped": dropped},
            events=[{"type": "artifact", "path": f"{base}/legal/"}])

    def _r2_i18n(self, req: HarnessRequest, provider, store, state: dict) -> HarnessResult:
        base = self._base(req.run_id)
        languages = state["languages"]

        # mono-lingual 스킵
        if len(languages) <= 1 or "ko" not in languages:
            state["r2_skipped"] = "mono-lingual"
            state["step"] = "RC"
            self._save_state(store, req.run_id, state)
            return HarnessResult(
                text="R2 스킵(모노링구얼).",
                output_path=f"{base}/i18n/",
                meta={"source": "marker", "step": "R2", "skipped": "mono-lingual"},
                events=[])

        scene_copy = self._collect_scene_copy(store, req.run_id, languages)
        ko_copy = scene_copy.get("ko", {})
        plan_node = store.get(f"/{req.run_id}/brainstorming/plan.md")
        fm = _frontmatter(plan_node.content_text if plan_node else "")
        required_disclosures: list[str] = fm.get("disclosures") or []

        # LLM 호출
        user_payload = {
            "ko_copy": ko_copy,
            "translations": {l: scene_copy.get(l, {}) for l in languages if l != "ko"},
            "required_disclosures": required_disclosures,
        }
        messages = [Message("user", json.dumps(user_payload, ensure_ascii=False))]
        pspec = PromptSpec(persona=PERSONA_B, studio="review", step="R2")
        try:
            resp = provider.complete(messages, system=pspec.assemble(),
                                     meta=pspec.meta)
        except Exception:
            state["live_unavailable"] = True
            state["step"] = "RC"
            self._save_state(store, req.run_id, state)
            return HarnessResult(
                text="R2 LLM 실패(graceful).",
                output_path=f"{base}/i18n/",
                meta={"source": "marker", "step": "R2", "live_unavailable": True},
                events=[])

        data = _parse_json(resp.text)
        if not data:
            state["parse_failed"] = True
            llm_findings: list = []
        else:
            llm_findings = data.get("findings") or []

        # LLM finding 영속
        seen_missing: set[tuple[str, str]] = set()  # (lang, disclosure)
        for f in llm_findings:
            kind = f.get("kind", "")
            severity = f.get("severity", "warning")
            # missing_disclosure는 강제 critical
            if kind == "missing_disclosure":
                severity = "critical"
                seen_missing.add((f.get("lang", ""), f.get("disclosure", "")))
            self._persist_verdict(
                store, req.run_id, node="i18n",
                asset_id=f"design/final/{f.get('lang','')}/main.scene",
                lang=f.get("lang"),
                severity=severity,
                location={"slot": "disclosure", "lang": f.get("lang")},
                evidence=f.get("evidence", ""),
                kind=kind,
                disclosure=f.get("disclosure"))

        # 안전망: 키워드 매핑으로 missing_disclosure 추가 검출
        for lang in languages:
            if lang == "ko":
                continue
            body = " ".join(str(v) for v in scene_copy.get(lang, {}).values())
            missing = find_missing_disclosures(body, lang, required_disclosures)
            for disc in missing:
                if (lang, disc) in seen_missing:
                    continue
                self._persist_verdict(
                    store, req.run_id, node="i18n",
                    asset_id=f"design/final/{lang}/main.scene",
                    lang=lang,
                    severity="critical",
                    location={"slot": "disclosure", "lang": lang},
                    evidence=f"안전망: 키워드 매핑이 '{disc}' 보존 미검출",
                    kind="missing_disclosure",
                    disclosure=disc)

        state["step"] = "RC"
        self._save_state(store, req.run_id, state)
        return HarnessResult(
            text=f"R2 동등성 검토 완료 (LLM {len(llm_findings)}건 + 안전망).",
            output_path=f"{base}/i18n/",
            meta={"source": "marker", "step": "R2"},
            events=[{"type": "artifact", "path": f"{base}/i18n/"}])

    def _rc_controversy(self, req: HarnessRequest, provider, store, state: dict
                         ) -> HarnessResult:
        """RC 논란 검토 — 3경로(결정론 안전망 / LLM 맥락 / 라이브 비전)로 controversy verdict 발행."""
        from ..core.controversy_rules import (
            evaluate as _cx_evaluate, load_blacklist, load_visual_symbols,
        )
        base = self._base(req.run_id)
        languages = state["languages"]
        scene_copy = self._collect_scene_copy(store, req.run_id, languages)

        # 경로 1: 결정론 안전망(블랙리스트) — provider 불요 → mock 결정론의 뼈대.
        for f in _cx_evaluate(scene_copy):
            loc = f["location"]
            self._persist_verdict(
                store, req.run_id, node="controversy",
                asset_id=f"design/final/{loc.get('lang') or ''}/main.scene",
                lang=loc.get("lang"), severity=f.get("severity", "warning"),
                location=loc, evidence=f.get("evidence", ""),
                official_source_url=f.get("official_source_url") or None,
                kind=f.get("category"), identity=f.get("id"))

        # 경로 2: LLM 맥락 판정 — 블랙리스트 카테고리 grounding. mock=DemoProvider 콘텐츠 기반.
        categories = sorted({e.get("category", "") for e in load_blacklist() if e.get("category")})
        payload = {"scene_copy": scene_copy, "blacklist_categories": categories}
        messages = [Message("user", json.dumps(payload, ensure_ascii=False))]
        pspec = PromptSpec(persona=PERSONA_RC, studio="review", step="RC")
        try:
            resp = provider.complete(messages, system=pspec.assemble(), meta=pspec.meta)
            data = _parse_json(resp.text)
        except Exception:
            state["live_unavailable"] = True
            data = {}
        if not data:
            state["parse_failed"] = True
            data = {}
        for f in (data.get("findings") or []):
            loc = f.get("location") or {"slot": "controversy", "lang": None}
            self._persist_verdict(
                store, req.run_id, node="controversy",
                asset_id=f"design/final/{loc.get('lang') or ''}/main.scene",
                lang=loc.get("lang"), severity=f.get("severity", "warning"),
                location=loc, evidence=f.get("evidence", ""),
                official_source_url=f.get("source") or f.get("official_source_url"),
                kind=f.get("category"), identity=f.get("id"))

        # 경로 3: 라이브 비전 — v1.png에서 시각 심볼(도안·제스처) + 박힌 텍스트(OCR 역할)
        # + 그림/손동작(OCR·텍스트로는 못 잡는 영역) 대조. mock/fake=빈(FakeProvider.review_image
        # 는 프롬프트와 무관하게 항상 findings=[]) — 라이브 전용, best-effort.
        v1 = store.get(f"/{req.run_id}/design/design-system/components/visual/v1.png")
        if v1 is None:
            state["vision_skipped"].append("controversy/visual/v1.png")
        else:
            visual_symbols = load_visual_symbols()
            symbols_desc = "; ".join(
                f"{s.get('name', '')}({s.get('description', '')})" for s in visual_symbols
                if s.get("name"))
            vprompt = (
                "이 이미지는 금융 마케팅 비주얼입니다. 다음 블랙리스트 카테고리에 근거해 "
                f"사회 논란·평판 리스크를 판정하세요: {categories}. "
                "이미지에 박힌 텍스트(은어·숫자·문구)도 읽어 대조하세요. "
                f"이미지에 다음 시각 심볼·제스처(글자 아님, 도안·손동작)가 있는지도 판정하세요: "
                f"{symbols_desc}. 명확한 전범·극단주의 도안(욱일기·나치)은 severity=critical, "
                "주관적 커뮤니티 제스처(집게손·일베 손가락)는 warning. 정상적 손동작·유사 문양을 "
                "과잉 판정하지 말 것(확실치 않으면 무시하거나 warning). 정치 판단이 아니라 "
                "'이 요소가 논란과 연관돼 오해·물의를 부를 수 있다'는 평판 리스크만 근거와 함께. "
                'JSON: {"findings":[{"location":{"slot":"visual","lang":null},'
                '"category":"...","severity":"critical|warning","evidence":"...","source":"..."}, ...]}'
            )
            try:
                img_bytes = v1.blob if v1.blob else (v1.content_text or "").encode("utf-8")
                vresp = self._vision_provider.review_image(img_bytes, vprompt, mime="image/png")
                for f in (_parse_json(vresp.text).get("findings") or []):
                    self._persist_verdict(
                        store, req.run_id, node="controversy",
                        asset_id="design/design-system/components/visual/v1.png",
                        lang=None, severity=f.get("severity", "warning"),
                        location={"slot": "visual", "lang": None},
                        evidence=f.get("evidence", ""),
                        official_source_url=f.get("source") or f.get("official_source_url"),
                        kind=f.get("category"))
            except Exception:
                state["vision_failed"] = True
                state["vision_skipped"].append("controversy/visual/v1.png")

        state["step"] = "R3"
        self._save_state(store, req.run_id, state)
        return HarnessResult(
            text="RC 논란 검토 완료.",
            output_path=f"{base}/controversy/",
            meta={"source": "marker", "step": "RC"},
            events=[{"type": "artifact", "path": f"{base}/controversy/"}])

    def _load_all_verdicts(self, store, run_id: str) -> list[dict]:
        """legal/·i18n/ 하위의 모든 verdict.json을 로드해서 dict 리스트 반환."""
        out: list[dict] = []
        for prefix in (f"{self._base(run_id)}/legal/",
                       f"{self._base(run_id)}/i18n/",
                       f"{self._base(run_id)}/controversy/"):
            for n in store.list(prefix):
                if n.path.endswith("verdict.json"):
                    try:
                        out.append(json.loads(n.content_text))
                    except Exception:
                        continue
        return out

    def _r3_reconcile(self, req: HarnessRequest, provider, store, state: dict
                       ) -> HarnessResult:
        base = self._base(req.run_id)
        verdicts = self._load_all_verdicts(store, req.run_id)

        # LLM reconciler 호출
        user_payload = {"verdicts": verdicts}
        messages = [Message("user", json.dumps(user_payload, ensure_ascii=False))]
        pspec = PromptSpec(persona=PERSONA_C, studio="review", step="R3")
        try:
            resp = provider.complete(messages, system=pspec.assemble(),
                                     meta=pspec.meta)
            data = _parse_json(resp.text)
        except Exception:
            state["step_failed"] = "R3"
            data = {}
        if not data:
            state["parse_failed"] = True
            data = {}
        recommendations = data.get("recommendations") or []
        conflicts = data.get("conflicts_resolved") or []

        # 권장 영속 — rec_id = sha1(rec JSON)[:8] (결정론)
        for rec in recommendations:
            rec_id = "rec_" + hashlib.sha1(
                json.dumps(rec, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest()[:8]
            target = rec.get("target", "text")
            if target not in ("image", "text", "video"):
                target = "text"
            body = (
                f"# {rec.get('instruction','(no instruction)')}\n\n"
                f"- asset_id: `{rec.get('asset_id','')}`\n"
                f"- lang: `{rec.get('lang','')}`\n"
                f"- priority: {rec.get('priority','-')}\n"
                f"- related_verdict_ids: {rec.get('related_verdict_ids', [])}\n"
            )
            store.put(f"{base}/revise/{target}/{rec_id}.md", body,
                      source="marker", mime="text/markdown")

        # 게이트 산정 (5트리거 flags 반영)
        gate = compute_gate(verdicts, flags={
            "live_unavailable": state.get("live_unavailable", False),
            "parse_failed": state.get("parse_failed", False),
            "vision_failed": state.get("vision_failed", False),
            "step_failed": state.get("step_failed", ""),
            "vision_skipped": state.get("vision_skipped", []),
        })

        # report.md 골격 (frontmatter + 본문)
        report_lines = [
            "---",
            f"languages: {state.get('languages', [])}",
            "gate:",
            f"  status: {gate['status']}",
            f"  critical_count: {gate['critical_count']}",
            f"  warning_count: {gate['warning_count']}",
            "flags:",
            f"  live_unavailable: {state.get('live_unavailable', False)}",
            f"  vision_skipped: {state.get('vision_skipped', [])}",
            f"  parse_failed: {state.get('parse_failed', False)}",
            f"generated_at: {_now_iso()}",
            "---",
            "",
            "# 검토 보고서",
            "",
            "## 게이트 결과",
            f"{gate['status']} — critical {gate['critical_count']} / "
            f"warning {gate['warning_count']}.",
            "",
            "## R1 법률 검토 (요약)",
        ]
        def _is_uploaded(x: dict) -> bool:
            return str((x.get("location") or {}).get("slot", "")).startswith("uploaded")

        for v in [x for x in verdicts if x.get("node") == "legal" and not _is_uploaded(x)]:
            report_lines.append(
                f"- [{v.get('severity')}] {v.get('location',{}).get('slot')} · "
                f"{v.get('lang') or '-'} · {v.get('clause','-')} — "
                f"{v.get('evidence','')[:80]}")
        up_verdicts = [x for x in verdicts if x.get("node") == "legal" and _is_uploaded(x)]
        if up_verdicts:
            report_lines += ["", "## 업로드 소재 심의"]
            for v in up_verdicts:
                report_lines.append(
                    f"- [{v.get('severity')}] {v.get('asset_id', '-')} · "
                    f"{v.get('clause', '-')} — {v.get('evidence', '')[:80]}")
        report_lines += ["", "## R2 동등성 검토 (요약)"]
        for v in [x for x in verdicts if x.get("node") == "i18n"]:
            report_lines.append(
                f"- [{v.get('severity')}] {v.get('lang','-')} · "
                f"{v.get('kind','-')} — {v.get('evidence','')[:80]}")
        report_lines += ["", "## RC 논란 검토 (요약)"]
        for v in [x for x in verdicts if x.get("node") == "controversy"]:
            report_lines.append(
                f"- [{v.get('severity')}] {v.get('kind','-')} · "
                f"{v.get('lang') or '-'} — {v.get('evidence','')[:80]}")
        report_lines += ["", "## 권장 수정 (우선순위 순)"]
        for rec in sorted(recommendations, key=lambda r: r.get("priority", 99)):
            report_lines.append(
                f"- ({rec.get('target','text')}) {rec.get('lang','-')} — "
                f"{rec.get('instruction','')[:120]}")
        report_lines += ["", "## Conflicts Resolved"]
        for c in conflicts:
            report_lines.append(f"- {c.get('summary','-')}")

        store.put(f"{base}/report.md", "\n".join(report_lines),
                  source="marker", mime="text/markdown")

        # 게이트 → manifest.step_status
        store.set_step_status(req.run_id, "review", gate["status"])
        state["step"] = "done"
        state["last_run_at"] = _now_iso()
        self._save_state(store, req.run_id, state)
        return HarnessResult(
            text=f"검토 완료 — {gate['status']} "
                 f"(critical {gate['critical_count']}, warning {gate['warning_count']}).",
            output_path=f"{base}/report.md",
            meta={"source": "marker", "step": "R3"},
            gate=GateEnvelope(kind="status", status=gate["status"],
                              critical_count=gate["critical_count"],
                              warning_count=gate["warning_count"],
                              actions=_actions_for(gate["status"])),
            events=[{"type": "artifact", "path": f"{base}/report.md"}])

    def _restart(self, req: HarnessRequest, store, state: dict) -> HarnessResult:
        """state 리셋 + 멱등 cleanup → R0부터 full 재검토."""
        state.update({
            "step": "R0", "matrix": {}, "acknowledged": False,
            "live_unavailable": False, "parse_failed": False,
            "vision_failed": False, "step_failed": "",
            "vision_skipped": [], "dropped_findings_count": 0,
            "r2_skipped": "",
        })
        self._save_state(store, req.run_id, state)
        # R0가 자체 cleanup 수행
        return self._r0_setup(req, store, state)

    def _ack(self, req: HarnessRequest, store, state: dict) -> HarnessResult:
        """WARN 상태에서 사용자 확인 → state.acknowledged=true. step_status는 WARN 유지."""
        m = store.get_manifest(req.run_id)
        current = m.step_status.get("review") if m else None
        if current != "WARN":
            return HarnessResult(
                text=f"ack은 WARN 상태에서만 유효합니다 (현재: {current}).",
                output_path=f"{self._base(req.run_id)}/_state.json",
                meta={"source": "marker", "step": state["step"], "ack_ignored": True},
                events=[])
        state["acknowledged"] = True
        self._save_state(store, req.run_id, state)
        return HarnessResult(
            text="경고를 확인했습니다. deploy 진입이 해제됩니다.",
            output_path=f"{self._base(req.run_id)}/_state.json",
            meta={"source": "marker", "step": "done", "acknowledged": True},
            events=[{"type": "artifact",
                     "path": f"{self._base(req.run_id)}/_state.json"}])

    def _regenerate(self, req: HarnessRequest, store, state: dict) -> HarnessResult:
        """직전 완료 step 재실행 (M4 DesignHarness 패턴 미러)."""
        idx = STEPS.index(state["step"]) if state["step"] in STEPS else 0
        prev = STEPS[idx - 1] if idx > 0 else None
        if not prev or prev == "done":
            return HarnessResult(
                text="재실행할 이전 단계가 없습니다.",
                output_path=f"{self._base(req.run_id)}/_state.json",
                meta={"source": "marker", "step": state["step"]}, events=[])
        state["step"] = prev
        self._save_state(store, req.run_id, state)
        return HarnessResult(
            text=f"{prev} 단계로 되돌렸습니다. 다음 호출에서 재실행됩니다.",
            output_path=f"{self._base(req.run_id)}/_state.json",
            meta={"source": "marker", "step": prev}, events=[])
