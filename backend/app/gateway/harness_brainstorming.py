"""BrainstormingHarness — 멀티턴 대화로 spec→plan 생성(stateless 재개).

LLM 응답 프로토콜(JSON): {"reply": str, "document": str, "ask": {...}|null, "ready": bool}
- document = 갱신된 전체 산출물(frontmatter+본문). 멱등 재작성(전체 갱신).
"""
from __future__ import annotations

import json

from ..providers.base import Message
from .critic import CriticVerdict
from .harness import GateEnvelope, Harness, HarnessRequest, HarnessResult
from .prompt import PromptSpec
from .state import load_state, save_state
from ..core.parsing import parse_json_block as _parse_json

# O4 compaction (spec: docs/specs/2026-06-02-messages-compaction-o4-design.md)
COMPACT_INPUT_TOKENS = 100_000   # 직전 응답 usage.input_tokens 임계
COMPACT_TURN_CAP = 20            # usage None 폴백: len(msgs) 임계(메시지 수)
KEEP_RECENT = 8                  # 요약 후 원문 보존 최근 메시지 수
MAX_FIELD_CHARS = 16 * 1024      # 개별 메시지 content 절단 임계(claw-code 미러)
_TRUNC_MARKER = "… [truncated]"

# medium 분기(spec §5.2): 공유 필드 + 매체별 필드. 기본 image(하위호환).
_PLAN_SHARED = {"material_matrix", "copy_themes", "multinational",
                "languages", "factsheet", "disclosures"}
_PLAN_IMAGE = {"creative_direction", "image_concept", "slots"}
_PLAN_VIDEO = {"video_direction", "footage_concept", "scene_beats"}
# image 기본값 유지(기존 import·테스트 표면 보존: _PLAN_SHARED|_PLAN_IMAGE == 기존 9키).
REQUIRED_PLAN_FIELDS = _PLAN_SHARED | _PLAN_IMAGE

# spec.md 충분성 게이트(Stage A) — Stage A system 프롬프트가 요구하는 9개 키와 동일.
# ready=true여도 이 키가 빠졌으면 확정(b) 대신 보충(c)을 띄워 '충분조건 미달 spec 확정'을 차단.
REQUIRED_SPEC_FIELDS = {
    "goal", "target_segments", "key_messages", "channels",
    "languages", "multinational", "tone", "factsheet", "disclosures",
}


def required_plan_fields(medium: str) -> set[str]:
    """medium별 plan.md 필수 frontmatter 키 집합."""
    extra = _PLAN_VIDEO if medium == "video" else _PLAN_IMAGE
    return _PLAN_SHARED | extra


def _medium_of(md: str) -> str:
    """frontmatter의 medium 값(없으면 image). 단순 라인 스캔(_frontmatter_keys와 동류)."""
    md = (md or "").lstrip()
    if md.startswith("---"):
        end = md.find("\n---", 3)
        block = md[3:end] if end > 0 else ""
        for line in block.splitlines():
            if line.strip().startswith("medium:"):
                return line.split(":", 1)[1].strip().strip('"\'').lower() or "image"
    return "image"

# Stage A 웹검색 마커 — provider(anthropic/google/openai)가 `if tools`로 truthy만 검사하므로
# 내용은 무시되고 각자 네이티브 검색(web_search_20250305 / google_search / web_search_options)을 켠다.
WEB_SEARCH_TOOL = [{"type": "web_search"}]

PERSONA = (
    "당신은 금융 마케팅 캠페인 기획 전문가입니다. 타겟 세그멘테이션·메시지 전략·채널 믹스·"
    "카피 방향·컴플라이언스(표시광고·금융광고)·리서치 기반 의사결정에 능합니다. "
    "한 번에 하나의 핵심 질문만 던지며, 사용자와 대화하며 기획을 점진적으로 구체화합니다."
)

_PROTOCOL = (
    "\n\n반드시 아래 JSON 한 개만 출력하세요(코드펜스 없이):\n"
    '{"reply": "사용자에게 보일 대화 응답(필요 시 질문 하나)", '
    '"document": "갱신된 전체 문서(--- YAML frontmatter --- 다음 마크다운 본문)", '
    '"ask": null 또는 {"trigger":"a|b|c","question":"...","options":["..."]}, '
    '"ready": true/false}'
)

# Stage A 지시 블록 — PromptSpec.constraints 단일 원소(문자열은 인라인 시절과 동일, D6).
STAGE_A_INSTR = (
    "\n\n[Stage A] 먼저 사용자와 대화하며 캠페인 기획에 필요한 정보를 한 번에 하나씩 질문해 모읍니다. "
    "정보가 충분해지기 전에는 document를 빈 문자열(\"\")로 두고 reply로만 대화하세요(이때 spec 파일은 생성되지 않습니다). "
    "충분히 모이면 그때 document에 spec.md 전체를 작성하세요 — "
    "goal/target_segments/key_messages/channels/languages/multinational/tone/factsheet/disclosures를 "
    "YAML frontmatter로 담고, 작성을 마치면 ready=true로 표시합니다. "
    "시장·트렌드·경쟁사 등 외부 사실이 필요하면 웹검색으로 직접 확인해 반영하고, 불확실하면 사용자에게 질문하세요."
)

# 요약자(컴팩션) 페르소나 — PromptSpec.persona(문자열은 인라인 시절과 동일, D6).
COMPACT_PERSONA = (
    "당신은 금융 마케팅 캠페인 기획 대화의 요약자입니다. "
    "확정된 사실(goal·target_segments·key_messages·channels·languages·"
    "multinational·tone·factsheet·disclosures)만 골라 최대한 짧게 요약합니다. "
    "표·머리말·수식어·인사말 없이 'key: value' 한 줄씩, 확정 안 된 항목은 생략하세요. "
    "이것은 후속 대화의 컨텍스트로 쓰일 압축 메모이므로 재진술·부연 없이 핵심만 남깁니다."
)


def _to_gate(ask: dict | None) -> "GateEnvelope | None":
    if not ask:
        return None
    return GateEnvelope(kind="ask",
                        trigger=str(ask.get("trigger", "")),
                        question=str(ask.get("question", "")),
                        options=list(ask.get("options") or []),
                        actions=["answer"])


def _frontmatter_keys(md: str) -> set[str]:
    md = (md or "").lstrip()
    if not md.startswith("---"):
        return set()
    end = md.find("\n---", 3)
    block = md[3:end] if end > 0 else ""
    keys = set()
    for line in block.splitlines():
        if line and not line[0].isspace() and ":" in line:
            keys.add(line.split(":", 1)[0].strip())
    return keys


class BrainstormingHarness(Harness):
    def system_prompt(self) -> str:
        return PERSONA

    def critic(self, plan_md: str) -> CriticVerdict:
        """⓪계약 검증: plan.md frontmatter의 REQUIRED_PLAN_FIELDS 누락을 검사.

        CriticVerdict(spec §6) 반환 — issues=정렬된 누락 필드 목록, passed=누락 없음.
        (T6에서 베이스 Harness.critic이 제거됨 — 이 critic 패밀리의 출력 봉투는
        gateway/critic.py CriticVerdict로 표준화.)
        """
        required = required_plan_fields(_medium_of(plan_md))
        missing = sorted(required - _frontmatter_keys(plan_md))
        return CriticVerdict(passed=not missing, issues=missing)

    def critic_spec(self, spec_md: str) -> CriticVerdict:
        """충분성 게이트: spec.md frontmatter의 REQUIRED_SPEC_FIELDS 누락을 검사.

        critic(plan)과 대칭(CriticVerdict 반환). Stage A에서 ready라도 누락이 있으면
        (c) 보충으로 유도해 '충분조건이 모두 모이지 않은 spec'이 확정(b)으로 넘어가는 것을 막는다.
        """
        missing = sorted(REQUIRED_SPEC_FIELDS - _frontmatter_keys(spec_md))
        return CriticVerdict(passed=not missing, issues=missing)

    # --- 상태 I/O (stateless 재개의 단일 소스) ---
    def _base(self, run_id: str) -> str:
        return f"/{run_id}/brainstorming"

    def _load_state(self, store, run_id: str) -> dict:
        return load_state(store, run_id, "brainstorming", default_factory=lambda: {
            "stage": "A", "spec_locked": False, "plan_locked": False,
            "pending_ask": None, "compaction": None, "last_input_tokens": 0})

    def _save_state(self, store, run_id: str, state: dict) -> None:
        save_state(store, run_id, "brainstorming", state)

    def _load_messages(self, store, run_id: str) -> list[dict]:
        n = store.get(f"{self._base(run_id)}/_messages.json")
        if n and n.content_text:
            return json.loads(n.content_text)
        return []

    def _save_messages(self, store, run_id: str, msgs: list[dict]) -> None:
        store.put(f"{self._base(run_id)}/_messages.json", json.dumps(msgs, ensure_ascii=False),
                  source="marker", mime="application/json")

    def handle_turn(self, req: HarnessRequest, *, provider, store) -> HarnessResult:
        state = self._load_state(store, req.run_id)
        msgs = self._load_messages(store, req.run_id)
        msgs.append({"role": "user", "content": req.user_prompt})
        if state["stage"] == "A":
            return self._stage_a(req, provider, store, state, msgs)
        if state["stage"] == "B":
            return self._stage_b(req, provider, store, state, msgs)
        return self._stage_done(req, provider, store, state, msgs)

    def _truncate_msg(self, m: dict) -> Message:
        """provider 입력 뷰용 필드 절단. 영속 _messages.json은 불변(비파괴)."""
        content = m.get("content", "")
        if len(content) > MAX_FIELD_CHARS:
            keep = MAX_FIELD_CHARS - len(_TRUNC_MARKER)
            content = content[:keep] + _TRUNC_MARKER
        return Message(m["role"], content)

    def _summarize(self, provider, prior: str, old: list[dict]) -> str:
        """오래된 턴을 현재 턴 provider로 증분 요약. 캠페인 확정 사실 보존 우선."""
        pspec = PromptSpec(persona=COMPACT_PERSONA,
                           studio="brainstorming", step="compact")
        parts = []
        if prior:
            parts.append("[기존 요약]\n" + prior)
        convo = "\n".join(f"{m['role']}: {m.get('content', '')}" for m in old)
        parts.append("[추가 대화]\n" + convo)
        resp = provider.complete([Message("user", "\n\n".join(parts))],
                                 system=pspec.assemble(), meta=pspec.meta)
        return (resp.text or "").strip()

    def _window_for_provider(self, msgs: list[dict], state: dict,
                             provider) -> list[Message]:
        """provider 입력 뷰 구성. 임계 초과 시 오래된 턴을 증분 요약으로 접고
        최근 KEEP_RECENT만 원문 전달. _messages.json 원본은 건드리지 않는다(비파괴).

        state["compaction"]을 in-place 갱신하며, 영속은 호출부의 _save_state가 수행.
        """
        comp = state.get("compaction")
        covered = comp["covered_upto"] if comp else 0
        last_tok = state.get("last_input_tokens", 0)
        trigger = (last_tok > COMPACT_INPUT_TOKENS) or \
                  (last_tok == 0 and len(msgs) > COMPACT_TURN_CAP)   # usage None 폴백
        if trigger:
            boundary = max(covered, len(msgs) - KEEP_RECENT)
            old = msgs[covered:boundary]
            if old:
                prior = comp["summary"] if comp else ""
                try:
                    summary = self._summarize(provider, prior, old)
                    state["compaction"] = {
                        "summary": summary, "covered_upto": boundary,
                        "count": (comp["count"] + 1 if comp else 1)}
                except Exception:
                    pass   # 요약 실패 → 미갱신, 아래에서 가능한 만큼 보존
        comp = state.get("compaction")
        if comp:
            head = [Message("user", "[이전 대화 요약]\n" + comp["summary"])]
            return head + [self._truncate_msg(m) for m in msgs[comp["covered_upto"]:]]
        return [self._truncate_msg(m) for m in msgs]

    def _save_research(self, store, run_id: str, citations: list[dict]) -> int:
        base = self._base(run_id)
        existing = len(store.list(f"{base}/assets/research"))
        for i, c in enumerate(citations or []):
            p = f"{base}/assets/research/article/src_{existing + i}.md"
            body = c.get("snippet") or f"# {c.get('title') or ''}\n\n{c.get('url') or ''}"
            store.put(p, body, source="research",
                      meta={"source_url": c.get("url"), "title": c.get("title")}, mime="text/markdown")
        return len(citations or [])

    def _stage_a(self, req: HarnessRequest, provider, store, state: dict, msgs: list[dict]) -> HarnessResult:
        base = self._base(req.run_id)

        # 사용자가 직전 (b) spec-lock 질문에 '예'로 답함 → Stage B 진입
        pending = state.get("pending_ask") or {}
        if pending.get("trigger") == "b" and self._is_yes(req.answer):
            state["spec_locked"] = True; state["stage"] = "B"; state["pending_ask"] = None
            self._save_state(store, req.run_id, state)
            self._save_messages(store, req.run_id, msgs)
            return self._stage_b(req, provider, store, state, msgs, first=True)
        if pending.get("trigger") == "b":   # '아니오' → 계속 탐색
            state["pending_ask"] = None

        spec_node = store.get(f"{base}/spec.md")
        cur = spec_node.content_text if spec_node else ""
        # 조립 순서(D6): persona → [Stage A] 지시 → _PROTOCOL → [현재 spec.md] — 인라인 시절과 동일.
        pspec = PromptSpec(persona=self.system_prompt(),
                           constraints=[STAGE_A_INSTR],
                           output_schema=_PROTOCOL,
                           references=[f"\n\n[현재 spec.md]\n{cur}"],
                           studio="brainstorming", step="stage_a")
        # 웹서치 ON(Stage A): 모델 자율 검색(WEB_SEARCH_TOOL). citations는 _save_research로 영속.
        resp = provider.complete(self._window_for_provider(msgs, state, provider),
                                 system=pspec.assemble(), tools=WEB_SEARCH_TOOL, meta=pspec.meta)
        state["last_input_tokens"] = (resp.usage or {}).get("input_tokens", 0)
        data = _parse_json(resp.text)
        reply = (data.get("reply") or "").strip()
        document = (data.get("document") or "").strip()
        ask = data.get("ask")
        ready = bool(data.get("ready"))

        events = []
        # 인용이 있으면 보존(향후 검색 도입 대비) — 기본 경로에선 비어 no-op.
        self._save_research(store, req.run_id, resp.citations)
        # spec.md는 document가 있을 때만 기록(A2): 빈/절단 출력으로 빈 파일을 만들거나 기존 spec을 지우지 않음.
        if document:
            store.put(f"{base}/spec.md", document, source="marker", mime="text/markdown",
                      meta={"grounds": [c.get("url") for c in (resp.citations or [])
                                        if c.get("url")]})
            events.append({"type": "artifact", "path": f"{base}/spec.md"})
        # reply 폴백: 파싱 실패/빈 reply여도 사용자에게 무언가는 보여 침묵(휘발 체감)을 막는다.
        if not reply:
            reply = ("내용을 정리하지 못했어요. 원하는 캠페인을 조금만 더 구체적으로 알려주시겠어요?"
                     if not document else "초안을 정리했어요. 확인해 주세요.")

        # ready(+document) → 충분성 게이트. 누락 필드가 있으면 보충(c), 충족하면 확정(b).
        # bypass 경로는 제거됨 — 모든 spec은 충분성 검증 + 사람 confirm을 거친다.
        if ready and document and not ask:
            missing = self.critic_spec(document).issues
            if missing:
                ask = {"trigger": "c",
                       "question": f"기획(spec)에 다음 필수 항목이 빠졌습니다: {', '.join(missing)}. 보충할까요?",
                       "options": ["보충하기", "수동 편집"]}
            else:
                ask = {"trigger": "b", "question": "spec을 확정하고 계획(plan) 단계로 넘어갈까요?",
                       "options": ["예, plan으로", "아니오, 더 다듬기"]}

        msgs.append({"role": "assistant", "content": reply})
        self._save_messages(store, req.run_id, msgs)
        state["pending_ask"] = ask
        self._save_state(store, req.run_id, state)
        gate_obj = _to_gate(ask)
        if gate_obj:
            events.append({"type": "gate", "gate": gate_obj.to_dict()})
        return HarnessResult(text=reply, output_path=f"{base}/spec.md",
                             meta={"source": "marker", "stage": "A"}, gate=gate_obj, events=events)

    def _is_yes(self, answer: str | None) -> bool:
        if not answer:
            return False
        a = answer.strip().lower()
        # 부정 우선 가드: '아니오/아니요/no...'로 시작하면 즉시 False
        if a.startswith("아니") or a.startswith("no"):
            return False
        # 긍정: 통제된 옵션('예, ...'/'예') 접두, 또는 명시적 yes, 또는 확정/ plan으로 표지
        return a.startswith("예") or a in {"y", "yes"} or "plan으로" in a or "확정" in a

    def _stage_b(self, req: HarnessRequest, provider, store, state: dict, msgs: list[dict],
                 first: bool = False) -> HarnessResult:
        base = self._base(req.run_id)

        # 1) pending(b) = plan lock 확정 처리(LLM 불필요)
        pending = state.get("pending_ask") or {}
        if not first and pending.get("trigger") == "b":
            if self._is_yes(req.answer):
                state["plan_locked"] = True; state["stage"] = "done"; state["pending_ask"] = None
                store.set_step_status(req.run_id, "brainstorming", "done")   # D8
                self._save_state(store, req.run_id, state)
                done_msg = "계획을 확정했습니다. design 단계로 진행할 수 있습니다."
                msgs.append({"role": "assistant", "content": done_msg})
                self._save_messages(store, req.run_id, msgs)
                return HarnessResult(text=done_msg, output_path=f"{base}/plan.md",
                                     meta={"source": "marker", "stage": "done"},
                                     events=[{"type": "artifact", "path": f"{base}/plan.md"}])
            # '아니오' → 계속 다듬기(아래 LLM 호출로 진행)
            state["pending_ask"] = None

        # 2) plan 생성/갱신 (LLM). 컨텍스트는 system=로(프로바이더 무관 전달).
        spec = store.get(f"{base}/spec.md")
        plan_node = store.get(f"{base}/plan.md")
        cur_plan = plan_node.content_text if plan_node else ""
        # 조립 순서(D6): persona → [Stage B] 지시 → _PROTOCOL → [확정 spec.md] → [현재 plan.md] — 인라인 시절과 동일.
        # 지시 블록은 sorted(REQUIRED_PLAN_FIELDS) 동적 결합이라 상수 추출 대신 함수 내 f-string 유지.
        pspec = PromptSpec(
            persona=self.system_prompt(),
            constraints=[
                ("\n\n[Stage B] spec.md를 구현 가능한 plan.md로 변환합니다. "
                 "plan.md의 YAML frontmatter에 반드시 다음 키를 포함하세요: "
                 f"{sorted(required_plan_fields(_medium_of(spec.content_text if spec else '')))}. "
                 + ("medium=video면 video_direction(duration_sec·aspect·fps·pacing·mood)·"
                    "scene_beats(훅·혜택·신뢰·CTA)·footage_concept을 채우세요. "
                    if _medium_of(spec.content_text if spec else "") == "video" else ""))],
            output_schema=_PROTOCOL,
            references=[f"\n\n[확정 spec.md]\n{spec.content_text if spec else ''}",
                        f"\n\n[현재 plan.md]\n{cur_plan}"],
            studio="brainstorming", step="stage_b")
        resp = provider.complete(self._window_for_provider(msgs, state, provider),
                                 system=pspec.assemble(), meta=pspec.meta)
        state["last_input_tokens"] = (resp.usage or {}).get("input_tokens", 0)
        data = _parse_json(resp.text)
        reply = (data.get("reply") or "").strip()
        document = (data.get("document") or "").strip()
        events = []
        # plan.md는 document가 있을 때만 기록(A2): 빈/절단 출력으로 기존 plan을 지우지 않음.
        if document:
            store.put(f"{base}/plan.md", document, source="marker", mime="text/markdown")
            events.append({"type": "artifact", "path": f"{base}/plan.md"})
        else:
            document = cur_plan   # 평가·이후 로직은 기존 plan 기준
        if not reply:
            reply = ("계획을 정리하지 못했어요. 한 번 더 시도해 주세요."
                     if not document else "계획 초안입니다. 확인해 주세요.")

        # 3) ⓪계약 검증
        missing = self.critic(document).issues
        if missing:
            ask = {"trigger": "c", "question": f"계획에 다음 필수 요소가 빠졌습니다: {', '.join(missing)}. 보충할까요?",
                   "options": ["보충하기", "수동 편집"]}
        elif bool(data.get("ready")):
            ask = {"trigger": "b", "question": "계획(plan)을 확정할까요? (design 단계가 열립니다)",
                   "options": ["예, 확정", "아니오, 더 다듬기"]}
        else:
            ask = data.get("ask")

        msgs.append({"role": "assistant", "content": reply})
        self._save_messages(store, req.run_id, msgs)
        state["pending_ask"] = ask
        self._save_state(store, req.run_id, state)
        gate_obj = _to_gate(ask)
        if gate_obj:
            events.append({"type": "gate", "gate": gate_obj.to_dict()})
        return HarnessResult(text=reply, output_path=f"{base}/plan.md",
                             meta={"source": "marker", "stage": "B"}, gate=gate_obj, events=events)

    def _stage_done(self, req: HarnessRequest, provider, store, state: dict, msgs: list[dict]) -> HarnessResult:
        base = self._base(req.run_id)
        text = "이 캠페인의 기획·계획은 확정되었습니다. design 단계에서 이어서 작업하세요."
        msgs.append({"role": "assistant", "content": text})
        self._save_messages(store, req.run_id, msgs)
        return HarnessResult(text=text, output_path=f"{base}/plan.md",
                             meta={"source": "marker", "stage": "done"}, events=[])
