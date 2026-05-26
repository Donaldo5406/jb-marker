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


from app.providers.base import ProviderResponse
from app.core.legal_search import build_legal_messages, search_and_filter


def test_build_legal_messages_has_scene_copy_and_tools_marker():
    scene_copy = {"ko": {"headline": "확실히 수익!", "cta": "지금 가입"}}
    metadata = "콘티: 우상향 그래프"
    system, messages, tools = build_legal_messages(scene_copy, metadata, load_whitelist())
    # system은 페르소나 A
    assert "법률 검토" in system or "법률" in system
    # messages는 1개 user message에 scene copy 포함
    assert any("확실히 수익" in str(m.content) for m in messages)
    # tools에 web_search 포함
    assert any(t.get("name") == "web_search" or t.get("type") == "web_search" for t in tools)


def test_search_and_filter_parses_json_and_applies_whitelist(make_scripted):
    sp = make_scripted(complete_responses=[ProviderResponse(
        text='{"findings":[{"official_source_url":"https://law.go.kr/x","clause":"§3","location":{"slot":"headline","lang":"ko"},"severity":"critical","evidence":"확실히 수익"},{"official_source_url":"https://blog.com/x","clause":"§Y","location":{"slot":"headline","lang":"ko"},"severity":"warning","evidence":"x"}]}',
        model="x")])
    findings, dropped, meta = search_and_filter(
        sp, {"ko": {"headline": "확실히 수익"}}, "콘티", load_whitelist())
    assert len(findings) == 1
    assert findings[0]["clause"] == "§3"
    assert dropped == 1
    assert meta.get("live_unavailable") is False
    # provider call: tools 인자 전달됨
    assert sp.calls_complete[0]["tools"] is not None


def test_search_and_filter_graceful_on_exception(make_scripted):
    sp = make_scripted(complete_raises=RuntimeError("no key"))
    findings, dropped, meta = search_and_filter(
        sp, {"ko": {"headline": "x"}}, "콘티", load_whitelist())
    assert findings == []
    assert dropped == 0
    assert meta["live_unavailable"] is True


def test_search_and_filter_graceful_on_unparsable(make_scripted):
    sp = make_scripted(complete_responses=[ProviderResponse(text="not json", model="x")])
    findings, dropped, meta = search_and_filter(
        sp, {"ko": {"headline": "x"}}, "콘티", load_whitelist())
    assert findings == []
    assert meta["parse_failed"] is True
