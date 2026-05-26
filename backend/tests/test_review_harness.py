"""ReviewHarness — R0~R3 핸들러·게이트·ack·restart·factory 통합."""
import json
import pytest

from app.gateway.harness import HarnessRequest
from app.gateway.harness_review import ReviewHarness, STEPS, PERSONA_A, PERSONA_B, PERSONA_C
from app.providers.base import ProviderResponse
from app.providers.fake import FakeProvider
from app.vfs.factory import make_local_store


def _setup_run(store, run_id="r1", languages=None):
    """공통 셋업 — run 생성 + brain plan.md + design 산출 자리."""
    languages = languages or ["ko", "en"]
    store.create_run(run_id, languages=languages)
    plan_md = (
        "---\n"
        f"languages: {languages}\n"
        "factsheet:\n  rate: 5.2\n"
        "disclosures:\n  - 미래 수익 보장 아님\n"
        "  - 세전 금리, 우대조건 충족 시\n"
        "---\n"
        "# Plan\n"
    )
    store.put(f"/{run_id}/brainstorming/plan.md", plan_md,
              source="marker", mime="text/markdown")
    # design 산출 자리
    for lang in languages:
        store.put(f"/{run_id}/design/final/{lang}/main.scene",
                  json.dumps({"copy": {lang: {"headline": "쉽고 빠르게",
                                                "cta": "지금 가입",
                                                "disclosure": "고지 텍스트"}}}),
                  source="marker", mime="application/json")
    store.put(f"/{run_id}/design/metadata.md", "콘티: 우상향 그래프\n",
              source="marker", mime="text/markdown")
    store.put(f"/{run_id}/design/design-system/components/visual/v1.png",
              b"\x89PNG\x00fake", source="gemini", mime="image/png")
    return store, run_id


def test_steps_constant():
    assert STEPS == ("R0", "R1", "R2", "R3", "done")


def test_personas_defined():
    assert "법률 검토" in PERSONA_A or "법률" in PERSONA_A
    assert "동등성" in PERSONA_B
    assert "통합" in PERSONA_C or "reconciler" in PERSONA_C.lower()


def test_review_harness_initial_state(tmp_path):
    store = make_local_store(tmp_path)
    _setup_run(store)
    h = ReviewHarness(vision_provider=FakeProvider())
    # _state.json 부재 시 기본값
    state = h._load_state(store, "r1")
    assert state["step"] == "R0"
    assert state["acknowledged"] is False
