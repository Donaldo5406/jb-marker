"""PromptSpec 조립 결정론 + meta 신호 (spec §5.1)."""
from app.gateway.prompt import PromptSpec


def test_assemble_order_is_deterministic():
    spec = PromptSpec(persona="P", constraints=["\n\nC1", "\n\nC2"],
                      references=["\n\nR1"], output_schema="\n\nS",
                      studio="design", step="S1")
    assert spec.assemble() == "P\n\nC1\n\nC2\n\nS\n\nR1"


def test_assemble_minimal_is_persona_only():
    assert PromptSpec(persona="P").assemble() == "P"


def test_assemble_skips_none_schema_but_keeps_empty_string():
    assert PromptSpec(persona="P", output_schema=None).assemble() == "P"
    assert PromptSpec(persona="P", output_schema="").assemble() == "P"


def test_meta_carries_studio_and_step():
    spec = PromptSpec(persona="P", studio="review", step="R2")
    assert spec.meta == {"studio": "review", "step": "R2"}
    assert PromptSpec(persona="P").meta == {"studio": "", "step": ""}
