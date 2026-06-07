"""BrainstormingHarness — 멀티턴 대화로 spec→plan 생성(stateless 재개).

LLM 응답 프로토콜(JSON): {"reply": str, "document": str, "ask": {...}|null, "ready": bool}
- document = 갱신된 전체 산출물(frontmatter+본문). 멱등 재작성(전체 갱신).
"""
from __future__ import annotations

import json
import re

from ..providers.base import Message
from .harness import AskPayload, Harness, HarnessRequest, HarnessResult

# O4 compaction (spec: docs/specs/2026-06-02-messages-compaction-o4-design.md)
COMPACT_INPUT_TOKENS = 100_000   # 직전 응답 usage.input_tokens 임계
COMPACT_TURN_CAP = 20            # usage None 폴백: len(msgs) 임계(메시지 수)
KEEP_RECENT = 8                  # 요약 후 원문 보존 최근 메시지 수
MAX_FIELD_CHARS = 16 * 1024      # 개별 메시지 content 절단 임계(claw-code 미러)
_TRUNC_MARKER = "… [truncated]"

REQUIRED_PLAN_FIELDS = {
    "creative_direction", "material_matrix", "slots", "image_concept",
    "copy_themes", "multinational", "languages", "factsheet", "disclosures",
}

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

# bypass(빠른 진행) 시 system에 주입 — 대화 없이 즉시 전체 산출. demo._BYPASS_MARK와 짝.
# (실 LLM에도 의미 있음: bypass=질문 생략·즉시 완성. 평소 멀티턴 대화 흐름은 보존.)
_BYPASS_DIRECTIVE = (
    "\n\n[빠른 진행] 사용자가 즉시 진행을 원합니다. 추가 질문(ask) 없이 지금까지의 정보로 "
    "document를 완성하고 ready=true로 표시하세요."
)


def _parse_json(text: str) -> dict:
    """LLM 출력에서 첫 JSON 객체를 견고하게 추출."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        # greedy: 최외곽 중괄호 구간을 잡음(단일 JSON 객체 출력 가정). 다객체 텍스트엔 부적합.
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return {}
        return {}


def _to_ask(ask: dict | None) -> "AskPayload | None":
    if not ask:
        return None
    return AskPayload(trigger=str(ask.get("trigger", "")),
                      question=str(ask.get("question", "")),
                      options=list(ask.get("options") or []))


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

    def critic(self, plan_md: str) -> list[str]:
        """⓪계약 검증: 누락된 REQUIRED_PLAN_FIELDS를 정렬해 반환.

        주의: 베이스 Harness.critic(draft)->str(텍스트 패스스루)을 의도적으로 재정의.
        여기선 plan.md의 frontmatter 키를 검사해 '부족한 필드 목록'을 돌려준다.
        """
        return sorted(REQUIRED_PLAN_FIELDS - _frontmatter_keys(plan_md))

    # --- 상태 I/O (stateless 재개의 단일 소스) ---
    def _base(self, run_id: str) -> str:
        return f"/{run_id}/brainstorming"

    def _load_state(self, store, run_id: str) -> dict:
        n = store.get(f"{self._base(run_id)}/_state.json")
        if n and n.content_text:
            return json.loads(n.content_text)
        return {"stage": "A", "spec_locked": False, "plan_locked": False,
                "pending_ask": None, "compaction": None, "last_input_tokens": 0}

    def _save_state(self, store, run_id: str, state: dict) -> None:
        store.put(f"{self._base(run_id)}/_state.json", json.dumps(state, ensure_ascii=False),
                  source="marker", mime="application/json")

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

    def _summarize(self, provider, model: str, prior: str, old: list[dict]) -> str:
        """오래된 턴을 현재 턴 provider로 증분 요약. 캠페인 확정 사실 보존 우선."""
        sys = ("당신은 금융 마케팅 캠페인 기획 대화의 요약자입니다. "
               "확정된 사실(goal·target_segments·key_messages·channels·languages·"
               "multinational·tone·factsheet·disclosures)만 골라 최대한 짧게 요약합니다. "
               "표·머리말·수식어·인사말 없이 'key: value' 한 줄씩, 확정 안 된 항목은 생략하세요. "
               "이것은 후속 대화의 컨텍스트로 쓰일 압축 메모이므로 재진술·부연 없이 핵심만 남깁니다.")
        parts = []
        if prior:
            parts.append("[기존 요약]\n" + prior)
        convo = "\n".join(f"{m['role']}: {m.get('content', '')}" for m in old)
        parts.append("[추가 대화]\n" + convo)
        resp = provider.complete([Message("user", "\n\n".join(parts))],
                                 model=model, system=sys)
        return (resp.text or "").strip()

    def _window_for_provider(self, msgs: list[dict], state: dict,
                             provider, model: str) -> list[Message]:
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
                    summary = self._summarize(provider, model, prior, old)
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
            store.put(p, c.get("snippet") or "", source="research",
                      meta={"source_url": c.get("url"), "title": c.get("title")}, mime="text/markdown")
        return len(citations or [])

    def _stage_a(self, req: HarnessRequest, provider, store, state: dict, msgs: list[dict]) -> HarnessResult:
        base = self._base(req.run_id)

        # 사용자가 직전 (b) spec-lock 질문에 '예'로 답함 → Stage B 진입
        pending = state.get("pending_ask") or {}
        if pending.get("trigger") == "b" and (req.bypass or self._is_yes(req.answer)):
            state["spec_locked"] = True; state["stage"] = "B"; state["pending_ask"] = None
            self._save_state(store, req.run_id, state)
            self._save_messages(store, req.run_id, msgs)
            return self._stage_b(req, provider, store, state, msgs, first=True)
        if pending.get("trigger") == "b":   # '아니오' → 계속 탐색
            state["pending_ask"] = None

        spec_node = store.get(f"{base}/spec.md")
        cur = spec_node.content_text if spec_node else ""
        sys = self.system_prompt() + (
            "\n\n[Stage A] 먼저 사용자와 대화하며 캠페인 기획에 필요한 정보를 한 번에 하나씩 질문해 모읍니다. "
            "정보가 충분해지기 전에는 document를 빈 문자열(\"\")로 두고 reply로만 대화하세요(이때 spec 파일은 생성되지 않습니다). "
            "충분히 모이면 그때 document에 spec.md 전체를 작성하세요 — "
            "goal/target_segments/key_messages/channels/languages/multinational/tone/factsheet/disclosures를 "
            "YAML frontmatter로 담고, 작성을 마치면 ready=true로 표시합니다. "
            "외부 사실이 꼭 필요하면 그 사실을 사용자에게 질문해 확인하세요(자동 웹검색은 하지 않습니다)." + _PROTOCOL +
            f"\n\n[현재 spec.md]\n{cur}")
        if req.bypass:
            sys += _BYPASS_DIRECTIVE
        # 웹서치 OFF(B): 한 줄 프롬프트에 아티클을 자동 수집하지 않음 — 대화-우선.
        resp = provider.complete(self._window_for_provider(msgs, state, provider, req.provider),
                                 model=req.provider, system=sys)
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
            store.put(f"{base}/spec.md", document, source="marker", mime="text/markdown")
            events.append({"type": "artifact", "path": f"{base}/spec.md"})
        # reply 폴백: 파싱 실패/빈 reply여도 사용자에게 무언가는 보여 침묵(휘발 체감)을 막는다.
        if not reply:
            reply = ("내용을 정리하지 못했어요. 원하는 캠페인을 조금만 더 구체적으로 알려주시겠어요?"
                     if not document else "초안을 정리했어요. 확인해 주세요.")

        # ready(+document) → spec lock 제안(b). bypass면 즉시 Stage B 진입.
        if ready and document and not ask:
            if req.bypass:
                state["spec_locked"] = True; state["stage"] = "B"; state["pending_ask"] = None
                msgs.append({"role": "assistant", "content": reply})
                self._save_messages(store, req.run_id, msgs)
                self._save_state(store, req.run_id, state)
                return self._stage_b(req, provider, store, state, msgs, first=True)
            ask = {"trigger": "b", "question": "spec을 확정하고 계획(plan) 단계로 넘어갈까요?",
                   "options": ["예, plan으로", "아니오, 더 다듬기"]}

        msgs.append({"role": "assistant", "content": reply})
        self._save_messages(store, req.run_id, msgs)
        state["pending_ask"] = ask
        self._save_state(store, req.run_id, state)
        ask_obj = _to_ask(ask)
        if ask_obj:
            events.append({"type": "askuser", "ask": {"trigger": ask_obj.trigger,
                                                       "question": ask_obj.question,
                                                       "options": ask_obj.options}})
        return HarnessResult(text=reply, output_path=f"{base}/spec.md",
                             meta={"source": "marker", "stage": "A"}, ask=ask_obj, events=events)

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
            if req.bypass or self._is_yes(req.answer):
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
        sys = self.system_prompt() + (
            "\n\n[Stage B] spec.md를 구현 가능한 plan.md로 변환합니다. plan.md의 YAML frontmatter에 반드시 "
            f"다음 키를 포함하세요: {sorted(REQUIRED_PLAN_FIELDS)}. " + _PROTOCOL +
            f"\n\n[확정 spec.md]\n{spec.content_text if spec else ''}\n\n[현재 plan.md]\n{cur_plan}")
        if req.bypass:
            sys += _BYPASS_DIRECTIVE
        resp = provider.complete(self._window_for_provider(msgs, state, provider, req.provider),
                                 model=req.provider, system=sys)
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
        missing = self.critic(document)
        if missing:
            ask = {"trigger": "c", "question": f"계획에 다음 필수 요소가 빠졌습니다: {', '.join(missing)}. 보충할까요?",
                   "options": ["보충하기", "수동 편집"]}
        elif bool(data.get("ready")):
            if req.bypass:
                state["plan_locked"] = True; state["stage"] = "done"; state["pending_ask"] = None
                store.set_step_status(req.run_id, "brainstorming", "done")
                self._save_state(store, req.run_id, state)
                msgs.append({"role": "assistant", "content": reply})
                self._save_messages(store, req.run_id, msgs)
                return HarnessResult(text=reply, output_path=f"{base}/plan.md",
                                     meta={"source": "marker", "stage": "done"}, events=events)
            ask = {"trigger": "b", "question": "계획(plan)을 확정할까요? (design 단계가 열립니다)",
                   "options": ["예, 확정", "아니오, 더 다듬기"]}
        else:
            ask = data.get("ask")

        msgs.append({"role": "assistant", "content": reply})
        self._save_messages(store, req.run_id, msgs)
        state["pending_ask"] = ask
        self._save_state(store, req.run_id, state)
        ask_obj = _to_ask(ask)
        if ask_obj:
            events.append({"type": "askuser", "ask": {"trigger": ask_obj.trigger,
                          "question": ask_obj.question, "options": ask_obj.options}})
        return HarnessResult(text=reply, output_path=f"{base}/plan.md",
                             meta={"source": "marker", "stage": "B"}, ask=ask_obj, events=events)

    def _stage_done(self, req: HarnessRequest, provider, store, state: dict, msgs: list[dict]) -> HarnessResult:
        base = self._base(req.run_id)
        text = "이 캠페인의 기획·계획은 확정되었습니다. design 단계에서 이어서 작업하세요."
        msgs.append({"role": "assistant", "content": text})
        self._save_messages(store, req.run_id, msgs)
        return HarnessResult(text=text, output_path=f"{base}/plan.md",
                             meta={"source": "marker", "stage": "done"}, events=[])
