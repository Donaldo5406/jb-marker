import json

from app.providers.base import ProviderResponse


class StubProvider:
    """미리 정한 JSON 텍스트를 순서대로 반환(LLM 대체)."""
    def __init__(self, responses): self._r = list(responses); self.calls = []
    def complete(self, messages, *, model, system=None, tools=None, **kw):
        self.calls.append({"system": system, "tools": tools, "messages": messages})
        r = self._r.pop(0)
        return ProviderResponse(text=r["text"], model=model,
                               citations=r.get("citations", []), usage=r.get("usage"))


class _RaisingProvider:
    name = "raise"
    def complete(self, *a, **k):
        raise RuntimeError("summarize fail")


def _store():
    from app.vfs.local import LocalVfsStore
    s = LocalVfsStore(); s.create_run("rb"); return s


def test_critic_reports_missing_plan_fields():
    from app.gateway.harness_brainstorming import BrainstormingHarness
    h = BrainstormingHarness()
    md = "---\ncreative_direction: x\nlanguages: [ko]\n---\n본문"
    missing = h.critic(md)
    assert "factsheet" in missing and "slots" in missing
    assert "creative_direction" not in missing


def test_critic_empty_when_all_present():
    from app.gateway.harness_brainstorming import BrainstormingHarness, REQUIRED_PLAN_FIELDS
    h = BrainstormingHarness()
    fm = "\n".join(f"{k}: v" for k in REQUIRED_PLAN_FIELDS)
    assert h.critic(f"---\n{fm}\n---\nbody") == []


def test_state_roundtrip_default_stage_a():
    from app.gateway.harness_brainstorming import BrainstormingHarness
    h = BrainstormingHarness(); s = _store()
    st = h._load_state(s, "rb")
    assert st["stage"] == "A" and st["spec_locked"] is False
    st["stage"] = "B"; h._save_state(s, "rb", st)
    assert h._load_state(s, "rb")["stage"] == "B"


def test_stage_a_writes_spec_and_research_and_returns_reply():
    from app.gateway.harness_brainstorming import BrainstormingHarness
    from app.gateway.harness import HarnessRequest
    h = BrainstormingHarness(); s = _store()
    stub = StubProvider([{
        "text": json.dumps({"reply": "주력 채널은 무엇인가요?",
                            "document": "---\ngoal: 적금 캠페인\n---\n# 기획",
                            "ask": {"trigger": "a", "question": "주력 채널?", "options": ["카톡", "이메일"]},
                            "ready": False}),
        "citations": [{"url": "https://x.com", "title": "금리표", "snippet": "연 3.5%"}],
    }])
    req = HarnessRequest(run_id="rb", studio="brainstorming", user_prompt="30대 적금 캠페인", provider="fake", is_marker=True)
    res = h.handle_turn(req, provider=stub, store=s)
    assert res.text == "주력 채널은 무엇인가요?"
    assert res.ask is not None and res.ask.trigger == "a"
    assert s.get("/rb/brainstorming/spec.md").content_text.startswith("---")
    research = s.list("/rb/brainstorming/assets/research")
    assert len(research) >= 1 and research[0].meta.get("source_url") == "https://x.com"
    assert len(h._load_messages(s, "rb")) == 2  # user + assistant
    assert stub.calls[0]["tools"] is None  # B: Stage A 웹서치 OFF(아티클 자동수집 안 함)


def test_stage_a_conversation_turn_writes_no_spec():
    # 대화-우선(B): document가 빈 턴은 spec.md를 만들지 않고 reply로만 대화.
    from app.gateway.harness_brainstorming import BrainstormingHarness
    from app.gateway.harness import HarnessRequest
    h = BrainstormingHarness(); s = _store()
    stub = StubProvider([{"text": json.dumps(
        {"reply": "어떤 연령대를 타겟하나요?", "document": "",
         "ask": {"trigger": "a", "question": "연령대?", "options": ["20대", "30대"]}, "ready": False})}])
    req = HarnessRequest(run_id="rb", studio="brainstorming", user_prompt="적금 캠페인 만들자", provider="fake", is_marker=True)
    res = h.handle_turn(req, provider=stub, store=s)
    assert res.text == "어떤 연령대를 타겟하나요?"
    assert s.get("/rb/brainstorming/spec.md") is None  # 빈 document → spec 미생성
    assert res.ask is not None and res.ask.trigger == "a"


def test_stage_a_parse_failure_falls_back_and_keeps_spec():
    # 파싱 실패/절단(A2): 빈 spec으로 덮어쓰지 않고, 빈 reply 대신 폴백 안내를 돌려준다.
    from app.gateway.harness_brainstorming import BrainstormingHarness
    from app.gateway.harness import HarnessRequest
    h = BrainstormingHarness(); s = _store()
    s.put("/rb/brainstorming/spec.md", "---\ngoal: 기존\n---\n본문", source="marker", mime="text/markdown")
    stub = StubProvider([{"text": "JSON이 아닌 잘린 텍스트 {\"reply\": \"중간에 끊"}])
    req = HarnessRequest(run_id="rb", studio="brainstorming", user_prompt="계속", provider="fake", is_marker=True)
    res = h.handle_turn(req, provider=stub, store=s)
    assert res.text  # 빈 답장이 아니라 폴백 안내
    assert s.get("/rb/brainstorming/spec.md").content_text == "---\ngoal: 기존\n---\n본문"  # 기존 spec 보존


def test_stage_a_ready_proposes_b_when_not_bypass():
    from app.gateway.harness_brainstorming import BrainstormingHarness
    from app.gateway.harness import HarnessRequest
    h = BrainstormingHarness(); s = _store()
    stub = StubProvider([{"text": json.dumps(
        {"reply": "정리했습니다.", "document": "---\ngoal: x\n---\n본문", "ask": None, "ready": True})}])
    req = HarnessRequest(run_id="rb", studio="brainstorming", user_prompt="좋아 정리해줘", provider="fake", is_marker=True)
    res = h.handle_turn(req, provider=stub, store=s)
    assert res.ask is not None and res.ask.trigger == "b"
    assert h._load_state(s, "rb")["stage"] == "A"  # 아직 전환 전(사용자 확정 대기)


def _seed_stage_b(h, s):
    st = h._load_state(s, "rb"); st["stage"] = "B"; st["spec_locked"] = True
    h._save_state(s, "rb", st)
    s.put("/rb/brainstorming/spec.md", "---\ngoal: 적금\n---\n본문", source="marker", mime="text/markdown")


def test_b_accepts_spec_lock_from_pending_b_then_runs():
    from app.gateway.harness_brainstorming import BrainstormingHarness, REQUIRED_PLAN_FIELDS
    from app.gateway.harness import HarnessRequest
    h = BrainstormingHarness(); s = _store()
    st = h._load_state(s, "rb")
    st["pending_ask"] = {"trigger": "b", "question": "?", "options": ["예", "아니오"]}
    h._save_state(s, "rb", st)
    s.put("/rb/brainstorming/spec.md", "---\ngoal: x\n---\nb", source="marker", mime="text/markdown")
    full = "---\n" + "\n".join(f"{k}: v" for k in REQUIRED_PLAN_FIELDS) + "\n---\n계획"
    stub = StubProvider([{"text": json.dumps({"reply": "계획 초안입니다.", "document": full, "ask": None, "ready": True})}])
    req = HarnessRequest(run_id="rb", studio="brainstorming", user_prompt="예", provider="fake", is_marker=True, answer="예, plan으로")
    res = h.handle_turn(req, provider=stub, store=s)
    assert s.get("/rb/brainstorming/plan.md") is not None
    assert h._load_state(s, "rb")["stage"] == "B"   # plan 확정 전(다음 b 대기)
    assert res.ask is not None and res.ask.trigger == "b"  # plan lock 확인 요청


def test_b_missing_contract_field_asks_c():
    from app.gateway.harness_brainstorming import BrainstormingHarness
    from app.gateway.harness import HarnessRequest
    h = BrainstormingHarness(); s = _store(); _seed_stage_b(h, s)
    partial = "---\ncreative_direction: x\nlanguages: [ko]\n---\n계획"
    stub = StubProvider([{"text": json.dumps({"reply": "초안", "document": partial, "ask": None, "ready": True})}])
    req = HarnessRequest(run_id="rb", studio="brainstorming", user_prompt="계획 짜줘", provider="fake", is_marker=True)
    res = h.handle_turn(req, provider=stub, store=s)
    assert res.ask is not None and res.ask.trigger == "c"
    assert "factsheet" in res.ask.question  # 누락 필드 안내


def test_b_plan_lock_sets_step_done():
    from app.gateway.harness_brainstorming import BrainstormingHarness, REQUIRED_PLAN_FIELDS
    from app.gateway.harness import HarnessRequest
    h = BrainstormingHarness(); s = _store()
    st = h._load_state(s, "rb"); st["stage"] = "B"; st["spec_locked"] = True
    st["pending_ask"] = {"trigger": "b", "question": "plan 확정?", "options": ["예", "아니오"]}
    h._save_state(s, "rb", st)
    full_fm = "\n".join(f"{k}: v" for k in REQUIRED_PLAN_FIELDS)
    s.put("/rb/brainstorming/plan.md", f"---\n{full_fm}\n---\n계획", source="marker", mime="text/markdown")
    req = HarnessRequest(run_id="rb", studio="brainstorming", user_prompt="예", provider="fake", is_marker=True, answer="예")
    res = h.handle_turn(req, provider=None, store=s)  # plan lock 확정은 LLM 호출 불필요
    assert h._load_state(s, "rb")["stage"] == "done"
    assert s.get_manifest("rb").step_status["brainstorming"] == "done"


def test_a_ready_bypass_runs_through_to_done():
    # bypass 경로: Stage A ready → _stage_b(first=True) → plan 생성 → ready&bypass → done
    from app.gateway.harness_brainstorming import BrainstormingHarness, REQUIRED_PLAN_FIELDS
    from app.gateway.harness import HarnessRequest
    h = BrainstormingHarness(); s = _store()
    full = "---\n" + "\n".join(f"{k}: v" for k in REQUIRED_PLAN_FIELDS) + "\n---\n계획"
    stub = StubProvider([
        {"text": json.dumps({"reply": "spec 정리완료", "document": "---\ngoal: x\n---\n본문", "ask": None, "ready": True})},
        {"text": json.dumps({"reply": "plan 초안", "document": full, "ask": None, "ready": True})},
    ])
    req = HarnessRequest(run_id="rb", studio="brainstorming", user_prompt="끝까지 자동", provider="fake", is_marker=True, bypass=True)
    res = h.handle_turn(req, provider=stub, store=s)
    assert s.get("/rb/brainstorming/plan.md") is not None
    assert h._load_state(s, "rb")["stage"] == "done"
    assert s.get_manifest("rb").step_status["brainstorming"] == "done"


def test_spec_lock_decline_continues_exploring():
    # pending(b) + '아니오' → Stage B로 전환하지 않고 계속 탐색
    from app.gateway.harness_brainstorming import BrainstormingHarness
    from app.gateway.harness import HarnessRequest
    h = BrainstormingHarness(); s = _store()
    st = h._load_state(s, "rb")
    st["pending_ask"] = {"trigger": "b", "question": "?", "options": ["예, plan으로", "아니오, 더 다듬기"]}
    h._save_state(s, "rb", st)
    s.put("/rb/brainstorming/spec.md", "---\ngoal: x\n---\n본문", source="marker", mime="text/markdown")
    stub = StubProvider([{"text": json.dumps(
        {"reply": "더 다듬어요. 톤은 어떻게?", "document": "---\ngoal: x\ntone: 친근\n---\n본문",
         "ask": None, "ready": False})}])
    req = HarnessRequest(run_id="rb", studio="brainstorming", user_prompt="아니오, 더 다듬기",
                         provider="fake", is_marker=True, answer="아니오, 더 다듬기")
    res = h.handle_turn(req, provider=stub, store=s)
    assert h._load_state(s, "rb")["stage"] == "A"           # 전환 안 함
    assert h._load_state(s, "rb")["pending_ask"] is None     # (b) 소거
    assert len(stub.calls) == 1                              # 계속 탐색(LLM 1회 호출)


def test_is_yes_rejects_freetext_negatives():
    from app.gateway.harness_brainstorming import BrainstormingHarness
    h = BrainstormingHarness()
    assert h._is_yes("예") and h._is_yes("예, plan으로") and h._is_yes("예, 확정") and h._is_yes("yes")
    assert not h._is_yes("아니오, 더 다듬기")
    assert not h._is_yes("plan 말고 더 보자")   # 부분문자열 오탐 방지
    assert not h._is_yes(None) and not h._is_yes("")


def test_state_default_has_compaction_fields():
    from app.gateway.harness_brainstorming import BrainstormingHarness
    h = BrainstormingHarness(); s = _store()
    st = h._load_state(s, "rb")
    assert st["compaction"] is None
    assert st["last_input_tokens"] == 0


def test_truncate_long_field_marks_and_caps():
    from app.gateway.harness_brainstorming import BrainstormingHarness, MAX_FIELD_CHARS, _TRUNC_MARKER
    h = BrainstormingHarness()
    long = "x" * (MAX_FIELD_CHARS + 100)
    out = h._truncate_msg({"role": "user", "content": long})
    assert out.role == "user"
    assert out.content.endswith(_TRUNC_MARKER)
    assert len(out.content) <= MAX_FIELD_CHARS


def test_truncate_short_field_unchanged():
    from app.gateway.harness_brainstorming import BrainstormingHarness
    h = BrainstormingHarness()
    out = h._truncate_msg({"role": "assistant", "content": "short"})
    assert out.content == "short"


def test_summarize_calls_provider_with_prior_and_old():
    from app.gateway.harness_brainstorming import BrainstormingHarness
    h = BrainstormingHarness()
    sp = StubProvider([{"text": "요약 결과"}])
    old = [{"role": "user", "content": "30대 적금"},
           {"role": "assistant", "content": "채널은?"}]
    out = h._summarize(sp, "fake", "이전요약X", old)
    assert out == "요약 결과"
    sent = sp.calls[0]["messages"][0].content
    assert "이전요약X" in sent       # prior 포함
    assert "30대 적금" in sent       # old 본문 포함
    assert sp.calls[0]["system"] is not None


def _long_msgs(n):
    return [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"}
            for i in range(n)]


def test_window_no_compaction_under_threshold():
    from app.gateway.harness_brainstorming import BrainstormingHarness
    from app.providers.fake import FakeProvider
    h = BrainstormingHarness()
    msgs = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]
    state = {"compaction": None, "last_input_tokens": 0}
    out = h._window_for_provider(msgs, state, FakeProvider(), "fake")
    assert len(out) == 2
    assert state["compaction"] is None


def test_window_token_trigger_summarizes_and_windows():
    from app.gateway.harness_brainstorming import BrainstormingHarness, KEEP_RECENT
    h = BrainstormingHarness()
    msgs = _long_msgs(20)
    state = {"compaction": None, "last_input_tokens": 200_000}  # 임계 초과
    sp = StubProvider([{"text": "요약본"}])
    out = h._window_for_provider(msgs, state, sp, "fake")
    assert out[0].role == "user" and out[0].content.startswith("[이전 대화 요약]")
    assert len(out) == 1 + KEEP_RECENT
    assert state["compaction"]["count"] == 1
    assert state["compaction"]["covered_upto"] == 20 - KEEP_RECENT
    assert len(msgs) == 20  # 비파괴: 원본 불변


def test_window_turn_cap_fallback_when_usage_none():
    from app.gateway.harness_brainstorming import BrainstormingHarness, COMPACT_TURN_CAP
    h = BrainstormingHarness()
    msgs = _long_msgs(COMPACT_TURN_CAP + 5)
    state = {"compaction": None, "last_input_tokens": 0}  # usage None 폴백
    sp = StubProvider([{"text": "요약"}])
    h._window_for_provider(msgs, state, sp, "fake")
    assert state["compaction"] is not None


def test_window_summary_failure_keeps_full_thread():
    from app.gateway.harness_brainstorming import BrainstormingHarness
    h = BrainstormingHarness()
    msgs = _long_msgs(21)
    state = {"compaction": None, "last_input_tokens": 200_000}
    out = h._window_for_provider(msgs, state, _RaisingProvider(), "fake")
    assert state["compaction"] is None      # 미갱신
    assert len(out) == 21                    # 전체 보존, 턴 실패 아님


def test_window_incremental_second_compaction_includes_prior():
    from app.gateway.harness_brainstorming import BrainstormingHarness, KEEP_RECENT
    h = BrainstormingHarness()
    msgs = _long_msgs(30)
    state = {"compaction": {"summary": "S1", "covered_upto": 12, "count": 1},
             "last_input_tokens": 200_000}
    sp = StubProvider([{"text": "S2"}])
    out = h._window_for_provider(msgs, state, sp, "fake")
    assert state["compaction"]["count"] == 2
    assert state["compaction"]["covered_upto"] == 30 - KEEP_RECENT
    assert "S1" in sp.calls[0]["messages"][0].content   # prior 요약 입력 포함
    assert out[0].content == "[이전 대화 요약]\nS2"


def test_window_legacy_state_without_keys():
    from app.gateway.harness_brainstorming import BrainstormingHarness
    from app.providers.fake import FakeProvider
    h = BrainstormingHarness()
    state = {"stage": "A"}  # compaction/last_input_tokens 키 없음(레거시)
    out = h._window_for_provider([{"role": "user", "content": "a"}], state, FakeProvider(), "fake")
    assert len(out) == 1


def test_handle_turn_persists_last_input_tokens():
    import json
    from app.gateway.harness_brainstorming import BrainstormingHarness
    from app.gateway.harness import HarnessRequest
    h = BrainstormingHarness(); s = _store()
    stub = StubProvider([{
        "text": json.dumps({"reply": "r", "document": "", "ask": None, "ready": False}),
        "usage": {"input_tokens": 12345, "output_tokens": 50}}])
    req = HarnessRequest(run_id="rb", studio="brainstorming",
                         user_prompt="hi", provider="fake", is_marker=True)
    h.handle_turn(req, provider=stub, store=s)
    assert h._load_state(s, "rb")["last_input_tokens"] == 12345


def test_handle_turn_compaction_is_nondestructive():
    import json
    from app.gateway.harness_brainstorming import BrainstormingHarness
    from app.gateway.harness import HarnessRequest
    h = BrainstormingHarness(); s = _store()
    # 긴 대화 사전 주입 + 임계 초과 상태
    msgs = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"}
            for i in range(20)]
    h._save_messages(s, "rb", msgs)
    st = h._load_state(s, "rb"); st["last_input_tokens"] = 200_000
    h._save_state(s, "rb", st)
    stub = StubProvider([
        {"text": "요약본"},   # _window_for_provider 내부 _summarize
        {"text": json.dumps({"reply": "ok", "document": "", "ask": None, "ready": False})},
    ])
    req = HarnessRequest(run_id="rb", studio="brainstorming",
                         user_prompt="다음 질문", provider="fake", is_marker=True)
    h.handle_turn(req, provider=stub, store=s)
    saved = h._load_messages(s, "rb")
    assert len(saved) == 22                       # 20 + user + assistant, 원본 보존
    assert h._load_state(s, "rb")["compaction"]["count"] == 1   # 압축은 발생


def test_window_truncates_tail_field_in_provider_view_only():
    # follow-up: tail에 든 과대 메시지가 provider 뷰에서 절단되고 영속 원본은 불변.
    from app.gateway.harness_brainstorming import (
        BrainstormingHarness, MAX_FIELD_CHARS, _TRUNC_MARKER)
    h = BrainstormingHarness()
    big = "y" * (MAX_FIELD_CHARS + 50)
    msgs = _long_msgs(18) + [{"role": "user", "content": big},
                             {"role": "assistant", "content": "ok"}]
    state = {"compaction": None, "last_input_tokens": 200_000}  # 토큰 트리거
    sp = StubProvider([{"text": "요약본"}])
    out = h._window_for_provider(msgs, state, sp, "fake")
    # 거대 메시지(index 18)는 tail(covered_upto=12 이후)에 포함 → 뷰에서 절단
    assert any(m.content.endswith(_TRUNC_MARKER) for m in out)
    assert all(len(m.content) <= MAX_FIELD_CHARS for m in out)
    # 영속 원본은 불변(비파괴)
    assert msgs[18]["content"] == big


def test_window_at_threshold_exact_no_trigger():
    # last_input_tokens == 임계는 '> 임계'가 아니므로 미트리거(경계).
    from app.gateway.harness_brainstorming import BrainstormingHarness, COMPACT_INPUT_TOKENS
    from app.providers.fake import FakeProvider
    h = BrainstormingHarness()
    msgs = _long_msgs(5)  # turn_cap(20) 미만 → 폴백도 안 걸림
    state = {"compaction": None, "last_input_tokens": COMPACT_INPUT_TOKENS}
    out = h._window_for_provider(msgs, state, FakeProvider(), "fake")
    assert state["compaction"] is None
    assert len(out) == 5


def test_window_token_trigger_but_thread_not_longer_than_keep_recent():
    # 트리거돼도 len(msgs) <= KEEP_RECENT면 old가 비어 요약 생략(compaction 미생성).
    from app.gateway.harness_brainstorming import BrainstormingHarness, KEEP_RECENT
    from app.providers.fake import FakeProvider
    h = BrainstormingHarness()
    msgs = _long_msgs(KEEP_RECENT)  # boundary = max(0, K-K) = 0 → old 빔
    state = {"compaction": None, "last_input_tokens": 200_000}
    out = h._window_for_provider(msgs, state, FakeProvider(), "fake")
    assert state["compaction"] is None
    assert len(out) == KEEP_RECENT


def test_window_compacted_no_retrigger_reuses_cached_summary():
    # 이미 압축됐고 임계 미만이면 재요약 없이 캐시 요약 재사용, provider 미호출.
    from app.gateway.harness_brainstorming import BrainstormingHarness
    h = BrainstormingHarness()
    msgs = _long_msgs(10)
    state = {"compaction": {"summary": "기존요약", "covered_upto": 2, "count": 1},
             "last_input_tokens": 50}  # < 임계, != 0 → 미트리거
    sp = StubProvider([])  # 호출되면 IndexError로 드러남
    out = h._window_for_provider(msgs, state, sp, "fake")
    assert state["compaction"]["count"] == 1            # 재요약 없음
    assert state["compaction"]["summary"] == "기존요약"   # 캐시 그대로
    assert len(sp.calls) == 0                            # provider 미호출
    assert out[0].content == "[이전 대화 요약]\n기존요약"
    assert len(out) == 1 + (10 - 2)                      # 요약 + msgs[2:]
