"""Usage tracking — observability.usage 모듈 + server API 통합."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.observability import pricing, usage as ulog
from app.server import create_app
from app import entitlement as ent


class _MemStore:
    """append-only put_text/get_text 메모리 stub — usage.record/read에 충분."""

    def __init__(self) -> None:
        self._t: dict[str, str] = {}

    def get_text(self, path: str) -> str | None:
        return self._t.get(path)

    def put_text(self, path: str, content: str) -> None:
        self._t[path] = content


def test_pricing_known_models() -> None:
    assert pricing.text_cost_usd("claude-sonnet-4-6", 1_000_000, 0) == pytest.approx(3.0)
    assert pricing.text_cost_usd("claude-sonnet-4-6", 0, 1_000_000) == pytest.approx(15.0)
    assert pricing.text_cost_usd("gemini-2.0-flash", 1_000_000, 0) == pytest.approx(0.10)
    assert pricing.image_cost_usd("gemini-2.5-flash-image", 5) == pytest.approx(0.20)


def test_pricing_unknown_returns_zero() -> None:
    assert pricing.text_cost_usd("future-model-x", 1000, 1000) == 0.0
    assert pricing.image_cost_usd("future-image-x", 3) == 0.0
    assert not pricing.is_known("future-model-x")


def test_record_and_summarize_text() -> None:
    s = _MemStore()
    ulog.record_usage(s, run_id="r1", step="brainstorming", model="claude-sonnet-4-6",
                      kind="text", usage={"input_tokens": 1000, "output_tokens": 500})
    ulog.record_usage(s, run_id="r1", step="brainstorming", model="claude-sonnet-4-6",
                      kind="text", usage={"input_tokens": 2000, "output_tokens": 800})
    summary = ulog.summarize(s, run_id="r1")
    assert summary["total"]["calls"] == 2
    assert summary["total"]["input_tokens"] == 3000
    assert summary["total"]["output_tokens"] == 1300
    assert summary["total"]["cost_usd"] > 0
    bs = summary["by_step"]["brainstorming"]
    assert bs["by_model"]["claude-sonnet-4-6"]["calls"] == 2


def test_record_image_kind() -> None:
    s = _MemStore()
    ulog.record_usage(s, run_id="r1", step="design", model="gemini-2.5-flash-image",
                      kind="image", images=2)
    summary = ulog.summarize(s, run_id="r1")
    assert summary["total"]["images"] == 2
    assert summary["total"]["cost_usd"] == pytest.approx(0.08)


def test_record_unknown_model_recorded_but_no_cost() -> None:
    s = _MemStore()
    ulog.record_usage(s, run_id="r1", step="x", model="mystery-1",
                      kind="text", usage={"input_tokens": 9999, "output_tokens": 9999})
    summary = ulog.summarize(s, run_id="r1")
    assert summary["total"]["calls"] == 1
    assert summary["total"]["cost_usd"] == 0.0
    assert summary["entries"][0]["known_model"] is False


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    monkeypatch.setenv("JBM_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ent.reset()
    return TestClient(create_app())


def test_usage_endpoint_empty_for_new_run(app_client) -> None:
    r = app_client.post("/runs", json={"title": "u", "languages": ["ko"]})
    run_id = r.json()["run_id"]
    res = app_client.get(f"/runs/{run_id}/usage")
    assert res.status_code == 200
    body = res.json()
    assert body["total"]["calls"] == 0
    assert body["entries"] == []


def test_usage_endpoint_404_unknown_run(app_client) -> None:
    res = app_client.get("/runs/nope/usage")
    assert res.status_code == 404


def test_advisor_live_records_usage(app_client, monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("ADVISOR_MODE", "live")
    ent.reset()
    client = TestClient(create_app())
    r = client.post("/runs", json={"title": "u", "languages": ["ko"]})
    run_id = r.json()["run_id"]
    client.post(f"/runs/{run_id}/deploy/setup", json={
        "selected_providers": ["sms"], "languages": ["ko"]})
    client.post(f"/runs/{run_id}/deploy/packages", json={
        "channel": "sms", "lang": "ko",
        "original_copy": "수익률 5%", "visual_path": "/x.png"})
    ent.set_dev_pass("demo")

    fake = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="다듬었습니다"),
            SimpleNamespace(type="tool_use", name="write_d2_copy",
                            input={"package_id": "sms_ko", "adapted_text": "수익률 5%"}),
        ],
        usage=SimpleNamespace(input_tokens=1200, output_tokens=300),
    )
    with patch("anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = fake
        chat = client.post(f"/runs/{run_id}/deploy/advisor/chat", json={
            "package_id": "sms_ko", "message": "짧게"})
    assert chat.status_code == 200

    res = client.get(f"/runs/{run_id}/usage")
    body = res.json()
    assert body["total"]["calls"] == 1
    assert body["total"]["input_tokens"] == 1200
    assert body["total"]["output_tokens"] == 300
    assert body["total"]["cost_usd"] > 0
    advisor = body["by_step"]["advisor"]
    assert advisor["calls"] == 1
    assert advisor["by_model"][next(iter(advisor["by_model"]))]["input_tokens"] == 1200
