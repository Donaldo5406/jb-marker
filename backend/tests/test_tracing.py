"""tracing 관측성 — no-op 보장·payload 정합성·예외 비전파 (spec 2026-06-12 §8)."""
from __future__ import annotations

from app.config import load_settings
from app.config import Settings
from app.observability import tracing
from app.providers.base import Message, ProviderResponse
from app.providers.wrappers import TrackedProvider


def _settings(**over):
    """필수 필드만 채운 Settings — 관측성 필드는 over로 주입."""
    base = dict(
        anthropic_api_key=None, openai_api_key=None, google_api_key=None,
        vfs_backend="local", entitlement_override=False, storage_dir="data/runs",
        anthropic_model="claude-sonnet-4-6", openai_model="gpt-4o",
        google_model="gemini-2.0-flash", advisor_mode="auto",
        anthropic_advisor_model="claude-sonnet-4-6",
    )
    base.update(over)
    return Settings(**base)


class FakeGeneration:
    def __init__(self, calls):
        self.calls = calls

    def update(self, **kw):
        self.calls.append(("update", kw))

    def update_trace(self, **kw):
        self.calls.append(("update_trace", kw))

    def end(self):
        self.calls.append(("end", {}))


class FakeLangfuse:
    def __init__(self):
        self.calls = []

    def start_generation(self, **kw):
        self.calls.append(("start_generation", kw))
        return FakeGeneration(self.calls)

    def flush(self):
        self.calls.append(("flush", {}))


def test_trace_id_deterministic_32hex():
    a = tracing._trace_id("run-abc")
    b = tracing._trace_id("run-abc")
    assert a == b
    assert len(a) == 32
    int(a, 16)  # hex 검증 — 비hex면 ValueError로 실패


def test_record_generation_noop_without_keys():
    # 키 없음 → 예외 없이 조용히 무동작이면 통과
    tracing.record_generation(_settings(), run_id="r1", step="design",
                              model="m", kind="text")


def test_record_generation_payload(monkeypatch):
    fake = FakeLangfuse()
    monkeypatch.setattr(tracing, "_get_client", lambda settings: fake)
    s = _settings(sentry_issues_url="https://org.sentry.io/issues")
    tracing.record_generation(
        s, run_id="r1", step="design", model="claude-sonnet-4-6", kind="text",
        input_payload={"messages": [{"role": "user", "content": "hi"}]},
        output_text="hello",
        usage={"input_tokens": 10, "output_tokens": 5},
    )
    names = [c[0] for c in fake.calls]
    assert names == ["start_generation", "update", "update_trace", "end"]
    start_kw = fake.calls[0][1]
    assert start_kw["name"] == "design/text"
    assert start_kw["model"] == "claude-sonnet-4-6"
    assert start_kw["trace_context"] == {"trace_id": tracing._trace_id("r1")}
    assert start_kw["metadata"]["run_id"] == "r1"
    assert start_kw["metadata"]["kind"] == "text"
    assert (start_kw["metadata"]["sentry_search_url"]
            == "https://org.sentry.io/issues/?query=run_id%3Ar1")
    upd_kw = fake.calls[1][1]
    assert upd_kw["output"] == "hello"
    assert upd_kw["usage_details"] == {"input": 10, "output": 5}
    trace_kw = fake.calls[2][1]
    assert trace_kw["name"] == "run:r1"


def test_record_generation_usage_none(monkeypatch):
    fake = FakeLangfuse()
    monkeypatch.setattr(tracing, "_get_client", lambda settings: fake)
    tracing.record_generation(_settings(), run_id="r1", step="design",
                              model="m", kind="image",
                              input_payload={"prompt": "p"}, output_text="<image>")
    upd_kw = fake.calls[1][1]
    assert upd_kw["usage_details"] is None


def test_record_generation_swallows_client_errors(monkeypatch):
    class Exploding:
        def start_generation(self, **kw):
            raise RuntimeError("boom")
    monkeypatch.setattr(tracing, "_get_client", lambda settings: Exploding())
    # 예외 미전파면 통과
    tracing.record_generation(_settings(), run_id="r1", step="s", model="m")


def test_tag_run_noop_without_dsn():
    # sentry_dsn 없음 + sentry_sdk 미설치 어느 쪽이든 예외 없으면 통과
    tracing.tag_run("r1", _settings())


def test_flush_noop_without_client():
    tracing.flush()


def test_load_settings_reads_observability_env(monkeypatch):
    # 로컬 .env 격리(아래 defaults 테스트와 동일 패턴) — LANGFUSE_HOST 디폴트 단언이
    # 로컬 .env의 호스트(예: jp.cloud)에 오염되지 않게 dotenv 재주입 차단 + 기존 env 제거.
    monkeypatch.setattr("app.config.load_dotenv", lambda: None)
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    monkeypatch.setenv("LANGFUSE_PROJECT_ID", "proj1")
    monkeypatch.setenv("SENTRY_DSN", "https://x@o0.ingest.sentry.io/1")
    monkeypatch.setenv("SENTRY_ISSUES_URL", "https://org.sentry.io/issues")
    s = load_settings()
    assert s.langfuse_public_key == "pk"
    assert s.langfuse_secret_key == "sk"
    assert s.langfuse_project_id == "proj1"
    assert s.langfuse_host == "https://cloud.langfuse.com"
    assert s.sentry_dsn == "https://x@o0.ingest.sentry.io/1"
    assert s.sentry_issues_url == "https://org.sentry.io/issues"


def test_settings_observability_defaults_none(monkeypatch):
    monkeypatch.setattr("app.config.load_dotenv", lambda: None)
    for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_PROJECT_ID",
              "SENTRY_DSN", "SENTRY_ISSUES_URL"):
        monkeypatch.delenv(k, raising=False)
    s = load_settings()
    assert s.langfuse_public_key is None
    assert s.langfuse_secret_key is None
    assert s.langfuse_project_id is None
    assert s.sentry_dsn is None
    assert s.sentry_issues_url is None


class _StubStore:
    """record_usage가 쓰는 최소 표면 — 메모리 텍스트 저장."""

    def __init__(self):
        self.texts = {}

    def get_text(self, p):
        return self.texts.get(p)

    def put_text(self, p, t):
        self.texts[p] = t


class _InnerProvider:
    name = "fake"
    _model = "fake-1"

    def complete(self, messages, *, model=None, system=None, **kw):
        return ProviderResponse(text="out", model="fake-1",
                                usage={"input_tokens": 1, "output_tokens": 2})

    def generate_image(self, prompt, *, aspect="1:1", image=None):
        return b"\x89PNG-stub"

    def review_image(self, image_bytes, prompt, *, mime="image/png"):
        return ProviderResponse(text='{"ok":true}', model="fake-1",
                                usage={"input_tokens": 3, "output_tokens": 4})


def _tracked(monkeypatch, recorded: list):
    monkeypatch.setattr(tracing, "record_generation",
                        lambda settings, **kw: recorded.append(kw))
    return TrackedProvider(_InnerProvider(), store=_StubStore(), run_id="r9",
                           step="design", settings=_settings())


def test_tracked_complete_records_generation(monkeypatch):
    recorded: list = []
    tp = _tracked(monkeypatch, recorded)
    tp.complete([Message(role="user", content="hi")], system="sys")
    assert len(recorded) == 1
    r = recorded[0]
    assert r["run_id"] == "r9" and r["step"] == "design" and r["kind"] == "text"
    assert r["model"] == "fake-1"
    assert r["output_text"] == "out"
    assert r["usage"] == {"input_tokens": 1, "output_tokens": 2}
    assert r["input_payload"]["system"] == "sys"
    assert r["input_payload"]["messages"] == [{"role": "user", "content": "hi"}]
    assert r["meta"] == {"cost_usd": 0.0}


def test_tracked_generate_image_records_generation(monkeypatch):
    recorded: list = []
    tp = _tracked(monkeypatch, recorded)
    tp.generate_image("a cat", aspect="16:9")
    r = recorded[0]
    assert r["kind"] == "image"
    assert r["input_payload"] == {"prompt": "a cat", "aspect": "16:9"}
    assert "bytes" in r["output_text"]
    assert r["meta"] == {"cost_usd": 0.0}


def test_tracked_review_image_records_generation(monkeypatch):
    recorded: list = []
    tp = _tracked(monkeypatch, recorded)
    tp.review_image(b"\x00\x01", "check this", mime="image/png")
    r = recorded[0]
    assert r["kind"] == "vision"
    assert r["input_payload"]["prompt"] == "check this"
    assert r["input_payload"]["image_bytes"] == 2
    assert r["output_text"] == '{"ok":true}'
    assert r["usage"] == {"input_tokens": 3, "output_tokens": 4}
    assert r["meta"] == {"cost_usd": 0.0}
