"""legal_search 모듈 — 화이트리스트 필터·메시지 빌드·search_and_filter 통합."""
import pytest

from app.core.legal_search import apply_whitelist, load_whitelist


def test_load_whitelist_has_5_domains():
    wl = load_whitelist()
    assert wl["version"] == "2026-05-26"
    assert "law.go.kr" in wl["domains"]
    assert len(wl["domains"]) >= 5


def test_apply_whitelist_keeps_official():
    findings = [
        {"official_source_url": "https://law.go.kr/lsInfoP.do?lsiSeq=1", "clause": "X"},
        {"official_source_url": "https://www.fss.or.kr/abc", "clause": "Y"},
    ]
    kept, dropped = apply_whitelist(findings, load_whitelist())
    assert len(kept) == 2
    assert dropped == 0


def test_apply_whitelist_drops_non_official():
    findings = [
        {"official_source_url": "https://random-blog.com/x", "clause": "X"},
        {"official_source_url": "https://law.go.kr/y", "clause": "Y"},
    ]
    kept, dropped = apply_whitelist(findings, load_whitelist())
    assert len(kept) == 1
    assert kept[0]["clause"] == "Y"
    assert dropped == 1


def test_apply_whitelist_subdomain_match():
    findings = [
        {"official_source_url": "https://sub.law.go.kr/x", "clause": "X"},
    ]
    kept, _ = apply_whitelist(findings, load_whitelist())
    assert len(kept) == 1


def test_apply_whitelist_missing_url_dropped():
    findings = [{"clause": "X"}]  # no official_source_url
    kept, dropped = apply_whitelist(findings, load_whitelist())
    assert kept == []
    assert dropped == 1
