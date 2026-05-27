"""server.py advisor 라우트의 mode 분기 검증 — env 조작으로 scripted/live/auto 흐름 확인."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.server import create_app
from app import entitlement as ent


@pytest.fixture
def client_factory(tmp_path, monkeypatch):
    monkeypatch.setenv("JBM_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("VFS_BACKEND", "local")

    def _make(*, mode: str, has_key: bool) -> TestClient:
        if has_key:
            monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        else:
            monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("ADVISOR_MODE", mode)
        ent.reset()
        return TestClient(create_app())

    return _make


def _setup_run_with_package(client: TestClient) -> tuple[str, str]:
    r = client.post("/runs", json={"title": "advisor mode", "languages": ["ko"]})
    run_id = r.json()["run_id"]
    client.post(f"/runs/{run_id}/deploy/setup", json={
        "selected_providers": ["sms"], "languages": ["ko"],
    })
    client.post(f"/runs/{run_id}/deploy/packages", json={
        "channel": "sms", "lang": "ko",
        "original_copy": "수익률 5%", "visual_path": "/x.png",
    })
    return run_id, "sms_ko"


def test_scripted_mode_no_llm_call(client_factory) -> None:
    client = client_factory(mode="scripted", has_key=True)
    run_id, pkg_id = _setup_run_with_package(client)
    ent.set_dev_pass("demo")
    with patch("anthropic.Anthropic") as mock_cls:
        res = client.post(f"/runs/{run_id}/deploy/advisor/chat", json={
            "package_id": pkg_id, "message": "짧게",
        })
    assert res.status_code == 200
    mock_cls.assert_not_called()
    body = res.json()
    assert body["status"] == "ok"
    assert any(tr["name"] == "write_d2_copy" for tr in body["tool_results"])


def test_auto_mode_without_key_falls_back_to_scripted(client_factory) -> None:
    client = client_factory(mode="auto", has_key=False)
    run_id, pkg_id = _setup_run_with_package(client)
    ent.set_dev_pass("demo")
    with patch("anthropic.Anthropic") as mock_cls:
        res = client.post(f"/runs/{run_id}/deploy/advisor/chat", json={
            "package_id": pkg_id, "message": "짧게",
        })
    assert res.status_code == 200
    mock_cls.assert_not_called()


def test_live_mode_without_key_returns_422(client_factory) -> None:
    client = client_factory(mode="live", has_key=False)
    run_id, pkg_id = _setup_run_with_package(client)
    ent.set_dev_pass("demo")
    res = client.post(f"/runs/{run_id}/deploy/advisor/chat", json={
        "package_id": pkg_id, "message": "짧게",
    })
    assert res.status_code == 422


def test_auto_mode_with_key_uses_live(client_factory) -> None:
    from types import SimpleNamespace
    client = client_factory(mode="auto", has_key=True)
    run_id, pkg_id = _setup_run_with_package(client)
    ent.set_dev_pass("demo")
    fake = SimpleNamespace(content=[
        SimpleNamespace(type="text", text="다듬었습니다"),
        SimpleNamespace(type="tool_use", name="write_d2_copy", input={
            "package_id": pkg_id, "adapted_text": "수익률 5%",
        }),
    ])
    with patch("anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = fake
        res = client.post(f"/runs/{run_id}/deploy/advisor/chat", json={
            "package_id": pkg_id, "message": "짧게",
        })
    assert res.status_code == 200
    mock_cls.assert_called_once()
    body = res.json()
    assert body["status"] == "ok"
    assert any(tr["name"] == "write_d2_copy" and tr["status"] == "ok" for tr in body["tool_results"])
