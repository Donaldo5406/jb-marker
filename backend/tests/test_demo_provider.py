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
