"""DEMO_LATENCY_MS — mock 자연 레이턴시 (spec 2026-07-04 D3). 기본 0=끔(테스트·CI 무영향)."""
import time

from app.providers.demo import DemoProvider


def _critic(provider: DemoProvider) -> None:
    provider.complete([], meta={"studio": "design", "step": "critic"})


def test_latency_default_off(monkeypatch):
    monkeypatch.delenv("DEMO_LATENCY_MS", raising=False)
    t0 = time.perf_counter()
    _critic(DemoProvider())
    assert time.perf_counter() - t0 < 0.1


def test_latency_env_paces_complete(monkeypatch):
    monkeypatch.setenv("DEMO_LATENCY_MS", "120")
    t0 = time.perf_counter()
    _critic(DemoProvider())
    assert time.perf_counter() - t0 >= 0.1


def test_latency_invalid_env_is_off(monkeypatch):
    monkeypatch.setenv("DEMO_LATENCY_MS", "abc")
    t0 = time.perf_counter()
    _critic(DemoProvider())
    assert time.perf_counter() - t0 < 0.1
