"""response_model 직렬화 회귀 가드 — wire 불변 (P4 T7, spec §8.2).

response_model 적용 후에도 분해 전 wire와 JSON 키셋·값이 동일해야 한다.
미지 키 탈락(모델 필드 누락)·None 키 추가(모델 필드 과잉) 양쪽을 정확
키셋 단언으로 핀한다.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.server import create_app


@pytest.fixture()
def c(monkeypatch, tmp_path):
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("JBM_STORAGE_DIR", str(tmp_path))
    return TestClient(create_app())


def test_health_exact_payload(c):
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_run_exact_keyset_and_title_echo(c):
    r = c.post("/runs", json={"title": "캠페인"})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"run_id", "title"}
    assert body["title"] == "캠페인"


def test_list_runs_exact_keyset(c):
    c.post("/runs", json={"title": "A"})
    r = c.get("/runs")
    assert r.status_code == 200
    runs = r.json()["runs"]
    assert runs
    assert set(runs[0].keys()) == {"run_id", "title", "created_at", "step_status"}


def test_vfs_put_exact_keyset(c):
    rid = c.post("/runs", json={}).json()["run_id"]
    r = c.put(f"/vfs/{rid}/design/x.md", json={"content": "본문"})
    assert r.status_code == 200
    assert set(r.json().keys()) == {"path", "mime", "source", "content_text", "meta"}


def test_vfs_get_text_exact_keyset_and_content(c):
    rid = c.post("/runs", json={}).json()["run_id"]
    c.put(f"/vfs/{rid}/design/x.md", json={"content": "본문"})
    r = c.get(f"/vfs/{rid}/design/x.md")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"path", "mime", "source", "content_text", "meta"}
    assert body["content_text"] == "본문"


def test_usage_empty_log_exact_total_keyset(c):
    rid = c.post("/runs", json={}).json()["run_id"]
    r = c.get(f"/runs/{rid}/usage")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"total", "by_step", "entries"}
    assert set(body["total"].keys()) == {
        "input_tokens", "output_tokens", "images", "cost_usd", "calls"}
    assert body["entries"] == []


def test_gallery_exact_keysets(c):
    rid = c.post("/runs", json={"title": "G"}).json()["run_id"]
    r = c.get(f"/runs/{rid}/gallery")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"run", "sections"}
    assert body["sections"]
    assert set(body["sections"][0].keys()) == {
        "studio", "label", "status", "has_preview", "groups"}


def test_preview_returns_html(c):
    rid = c.post("/runs", json={}).json()["run_id"]
    r = c.get(f"/runs/{rid}/preview")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
