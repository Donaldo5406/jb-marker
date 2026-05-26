"""D2 패키저 — copy_limits 분기·disclosures append."""
import pytest
from app.deploy.providers import get_provider
from app.deploy.packager import needs_advisor, append_disclosures, package_channel


def test_within_limits_no_advisor():
    p = get_provider("email")
    needs, _ = needs_advisor("짧은 카피", p)
    assert not needs


def test_over_limits_needs_advisor():
    p = get_provider("kakao")  # body limit 1000
    long = "x" * 1500
    needs, reason = needs_advisor(long, p)
    assert needs
    assert "1500" in reason


def test_disclosures_appended_when_missing():
    p = get_provider("kakao")  # required: 광고 표시·수신거부
    out = append_disclosures("본문", p)
    assert "광고 표시" in out
    assert "수신거부" in out


def test_disclosures_not_duplicated_when_present():
    p = get_provider("kakao")
    text_with = "본문 광고 표시 수신거부"
    out = append_disclosures(text_with, p)
    assert out.count("광고 표시") == 1


def test_package_ok_when_within_limits():
    p = get_provider("email")
    pkg = package_channel(channel="email", lang="ko", original_copy="짧은 카피", provider=p, visual_path="/x.png")
    assert pkg["status"] == "ok"
    assert pkg["grounding_check"] == "n/a"


def test_package_needs_advisor_when_over():
    p = get_provider("sms")  # body 90
    pkg = package_channel(channel="sms", lang="ko", original_copy="x" * 150, provider=p, visual_path="/x.png")
    assert pkg["status"] == "needs_advisor"
    assert pkg["original_text"] == "x" * 150
    assert pkg["disclosures"] == p.spec.required_disclosures
