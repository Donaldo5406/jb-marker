"""ledger 로더 — 기본값 주입·fixture 무수정 검증."""
import pytest
from app.deploy.ledger import load_ledger


def test_loads_512_recipients():
    ledger = load_ledger()
    assert len(ledger) == 512


def test_defaults_injected_when_missing():
    ledger = load_ledger()
    sample = ledger[0]
    assert sample["collected_purpose"] == "marketing"
    assert sample["collected_days_ago"] == 30


def test_original_fields_preserved():
    ledger = load_ledger()
    sample = ledger[0]
    # 03 fixture 원본 키
    for k in ["id", "marketing_consent", "opt_out", "night_consent", "last_same_product_days", "lang"]:
        assert k in sample


def test_languages_ko_vi_present():
    ledger = load_ledger()
    langs = {r["lang"] for r in ledger}
    assert {"ko", "vi"}.issubset(langs)
