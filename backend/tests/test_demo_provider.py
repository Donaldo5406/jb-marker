import json
from app.providers import demo_fixtures as F


def test_spec_md_has_required_frontmatter():
    spec = F.SPEC_MD
    for key in ("goal", "target_segments", "channels", "languages", "factsheet", "disclosures"):
        assert f"{key}:" in spec


def test_plan_md_has_all_required_plan_fields():
    from app.gateway.harness_brainstorming import REQUIRED_PLAN_FIELDS, _frontmatter_keys
    keys = _frontmatter_keys(F.PLAN_MD)
    assert REQUIRED_PLAN_FIELDS <= keys, f"missing: {REQUIRED_PLAN_FIELDS - keys}"


def test_layout_spec_shape():
    ls = F.LAYOUT_SPEC
    assert ls["slots"] and ls["visual_concept"] and ls["aspect"]
    assert all({"role", "copy_key"} <= set(s) for s in ls["slots"])


def test_layout_spec_bbox_is_object_form():
    """bbox는 레퍼런스·실 LLM·프론트 assembleScene과 동일한 {x,y,w,h} 객체 형식이어야 한다.
    배열([x,y,w,h])이면 프론트가 s.bbox.x로 읽어 좌표·크기가 전부 undefined가 되어
    텍스트가 원점에 겹치고 배경 이미지 scaleToWidth가 죽는다."""
    for s in F.LAYOUT_SPEC["slots"]:
        assert isinstance(s["bbox"], dict), f"{s['role']} bbox는 dict여야 함(배열 금지)"
        assert {"x", "y", "w", "h"} <= set(s["bbox"]), f"{s['role']} bbox에 x/y/w/h 필요"


def test_copy_numbers_are_grounded_in_factsheet():
    """copy의 모든 수치 토큰이 factsheet corpus에 있어야 grounding 통과."""
    from app.core.grounding import build_corpus, find_ungrounded
    corpus = build_corpus(F.FACTSHEET)
    for lang, fields in F.COPY.items():
        for role in ("headline", "body", "cta"):
            assert not find_ungrounded(fields.get(role, ""), corpus), f"{lang}.{role} ungrounded"


def test_critic_scores_pass():
    from app.gateway.harness_design import DesignHarness
    h = DesignHarness(image_provider=None)
    assert h.critic(F.CRITIC_SCORES)["pass"] is True


def test_placeholder_png_is_valid_png():
    png = F.placeholder_png()
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 100


def _complete(system: str):
    from app.providers.demo import DemoProvider
    from app.providers.base import Message
    return DemoProvider().complete([Message("user", "x")], model="demo", system=system)


def test_detect_stage_a_returns_spec_ready():
    r = json.loads(_complete("페르소나\n\n[Stage A] ... goal/target_segments ...").text)
    assert r["ready"] is True and "goal:" in r["document"]


def test_detect_stage_b_returns_plan_with_fields():
    r = json.loads(_complete("페르소나\n\n[Stage B] ... plan.md ...").text)
    assert r["ready"] is True and "creative_direction:" in r["document"]


def test_detect_s1_returns_layout_spec():
    r = json.loads(_complete("페르소나\n\n[S1 Rough] layout_spec ...").text)
    assert "slots" in r["layout_spec"]


def test_detect_s2b_returns_copy_4langs():
    r = json.loads(_complete("페르소나\n\n[S2b 카피·타이포] ...").text)
    assert set(r["copy"]) == {"ko", "en", "vi", "zh"}


def test_detect_critic_returns_passing_scores():
    r = json.loads(_complete("페르소나\n\n[자기-크리틱] hierarchy/grid ...").text)
    assert set(r["scores"]) >= {"hierarchy", "brand"}


def test_detect_review_b_returns_empty_findings():
    r = json.loads(_complete("당신은 금융 마케팅 다국어 동등성 검토관입니다.").text)
    assert r["findings"] == []


def test_demo_generate_image_is_placeholder_png():
    from app.providers.demo import DemoProvider
    png = DemoProvider().generate_image("concept", aspect="1:1")
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 1000  # 1x1보다 큼


def test_demo_review_image_empty_findings():
    from app.providers.demo import DemoProvider
    resp = DemoProvider().review_image(b"x", "prompt")
    assert json.loads(resp.text)["findings"] == []
