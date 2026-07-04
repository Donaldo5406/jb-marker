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


def test_latency_image_edit_skips_sleep(monkeypatch):
    """image 입력(편집·언어 변형) 베이크는 지연 생략 — 비주얼 스텝이 변형 3장 지연으로
    불필요하게 길어졌다(2026-07-05 스텝 레이턴시 단축). 신규 생성(image=None)만 페이싱."""
    monkeypatch.setenv("DEMO_LATENCY_MS", "200")
    slept: list[float] = []
    monkeypatch.setattr("app.providers.demo.time.sleep", lambda s: slept.append(s))
    DemoProvider().generate_image("- headline: x", image=b"\x89PNG")
    assert slept == []
    DemoProvider().generate_image("- headline: x")   # 신규 생성은 여전히 페이싱
    assert len(slept) == 1
