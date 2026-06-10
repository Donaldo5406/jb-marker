"""meta.grounds 영속 — spec.md(리서치 citation)·layout.spec.json(S2b grounding) (spec §7-5)."""
import json

from app.gateway.harness import HarnessRequest
from app.gateway.harness_brainstorming import BrainstormingHarness
from app.gateway.harness_design import DesignHarness
from app.providers.base import ProviderResponse
from app.vfs.local import LocalVfsStore


def _store(tmp_path):
    s = LocalVfsStore(storage_dir=str(tmp_path))
    s.create_run("r1")
    return s


class _CiteStub:
    name = "stub"

    def complete(self, messages, *, model=None, system=None, tools=None, **kw):
        return ProviderResponse(
            text=json.dumps({"reply": "정리했어요",
                             "document": "---\ngoal: g\n---\n본문",
                             "ask": None, "ready": False}, ensure_ascii=False),
            model="stub",
            citations=[{"url": "https://ex.com/a", "title": "t", "snippet": "s"}])


def test_stage_a_records_citation_grounds(tmp_path):
    s = _store(tmp_path)
    h = BrainstormingHarness()
    h.handle_turn(HarnessRequest(run_id="r1", studio="brainstorming",
                                 user_prompt="시작", provider="fake"),
                  provider=_CiteStub(), store=s)
    meta = s.read_meta("/r1/brainstorming/spec.md")
    assert meta["grounds"] == ["https://ex.com/a"]


class _CopyStub:
    name = "stub"

    def complete(self, messages, *, model=None, system=None, **kw):
        # 수치 없는 카피 — find_ungrounded 토큰 의미론과 무관하게 ungrounded=[]를 보장
        # (이 테스트의 목적은 grounding 로직이 아니라 'grounds 메타가 기록되는가').
        return ProviderResponse(
            text=json.dumps({"copy": {"ko": {"headline": "정기예금 안내",
                                             "body": "자세한 내용은 상품설명서를 확인하세요",
                                             "cta": "가입하기"}}}, ensure_ascii=False),
            model="stub")


def test_s2b_records_grounding_grounds(tmp_path):
    s = _store(tmp_path)
    s.put("/r1/brainstorming/plan.md",
          "---\nfactsheet:\n  rate: \"3.5%\"\n---\n본문",
          source="user", mime="text/markdown")
    s.put("/r1/design/_state.json", json.dumps({
        "step": "S2b", "gate": None, "confirmed": {}, "bypass": {},
        "languages": ["ko"], "pending_ask": None}), source="marker",
        mime="application/json")
    h = DesignHarness(image_provider=None)   # S2b는 이미지 액터 미사용
    h.handle_turn(HarnessRequest(run_id="r1", studio="design",
                                 user_prompt="카피 확정", provider="fake",
                                 is_marker=True),
                  provider=_CopyStub(), store=s)
    meta = s.read_meta("/r1/design/rough/layout.spec.json")
    assert meta["grounds"]["corpus"] == "factsheet"
    assert meta["grounds"]["ungrounded"] == []   # 수치 없는 카피라 전부 grounded
