def test_provider_response_has_citations_default_empty():
    from app.providers.base import ProviderResponse
    r = ProviderResponse(text="x", model="m")
    assert r.citations == []


def test_fake_provider_accepts_tools_and_returns_citation():
    from app.providers.fake import FakeProvider
    from app.providers.base import Message
    p = FakeProvider()
    r = p.complete([Message("user", "적금 금리 알려줘")], model="fake-1",
                   tools=[{"type": "web_search"}])
    assert r.text  # echo 포함
    assert len(r.citations) >= 1
    assert "url" in r.citations[0]
