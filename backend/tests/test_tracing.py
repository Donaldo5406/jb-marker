"""tracing 관측성 — no-op 보장·payload 정합성·예외 비전파 (spec 2026-06-12 §8)."""
from __future__ import annotations

from app.config import load_settings


def test_load_settings_reads_observability_env(monkeypatch):
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
    for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_PROJECT_ID",
              "SENTRY_DSN", "SENTRY_ISSUES_URL"):
        monkeypatch.delenv(k, raising=False)
    s = load_settings()
    assert s.langfuse_public_key is None
    assert s.langfuse_secret_key is None
    assert s.langfuse_project_id is None
    assert s.sentry_dsn is None
    assert s.sentry_issues_url is None
