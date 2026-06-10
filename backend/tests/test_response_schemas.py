"""response_model 직렬화 회귀 가드 — wire 불변 (P4 T7, spec §8.2).

response_model 적용 후에도 분해 전 wire와 JSON 키셋·값이 동일해야 한다.
미지 키 탈락(모델 필드 누락)·None 키 추가(모델 필드 과잉) 양쪽을 정확
키셋 단언으로 핀한다. local_client fixture는 conftest.py 공용.
"""
from __future__ import annotations

import base64
import struct
import zlib


def _png_1px() -> bytes:
    """유효한 1x1 투명 PNG 바이트 — 외부 픽스처 없이 결정론 생성."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data)))
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)  # 1x1, 8bit RGBA
    idat = zlib.compress(b"\x00\x00\x00\x00\x00")  # filter 0 + RGBA(0,0,0,0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


def test_health_exact_payload(local_client):
    r = local_client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_run_exact_keyset_and_title_echo(local_client):
    r = local_client.post("/runs", json={"title": "캠페인"})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"run_id", "title"}
    assert body["title"] == "캠페인"


def test_list_runs_exact_keyset(local_client):
    local_client.post("/runs", json={"title": "A"})
    r = local_client.get("/runs")
    assert r.status_code == 200
    runs = r.json()["runs"]
    assert runs
    assert set(runs[0].keys()) == {"run_id", "title", "created_at", "step_status"}


def test_vfs_put_exact_keyset(local_client):
    rid = local_client.post("/runs", json={}).json()["run_id"]
    r = local_client.put(f"/vfs/{rid}/design/x.md", json={"content": "본문"})
    assert r.status_code == 200
    assert set(r.json().keys()) == {"path", "mime", "source", "content_text", "meta"}


def test_vfs_put_base64_exact_keyset_and_null_text(local_client):
    """base64 PUT(blob 저장) 응답도 동일 키셋 — content_text는 None."""
    rid = local_client.post("/runs", json={}).json()["run_id"]
    b64 = base64.b64encode(_png_1px()).decode()
    r = local_client.put(f"/vfs/{rid}/design/icon.png",
                         json={"content": b64, "mime": "image/png",
                               "content_encoding": "base64"})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"path", "mime", "source", "content_text", "meta"}
    assert body["content_text"] is None


def test_vfs_get_text_exact_keyset_and_content(local_client):
    rid = local_client.post("/runs", json={}).json()["run_id"]
    local_client.put(f"/vfs/{rid}/design/x.md", json={"content": "본문"})
    r = local_client.get(f"/vfs/{rid}/design/x.md")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"path", "mime", "source", "content_text", "meta"}
    assert body["content_text"] == "본문"


def test_vfs_get_blob_binary_passthrough(local_client):
    """blob GET은 response_model을 우회해 바이너리 원문을 그대로 반환해야 한다."""
    raw = _png_1px()
    rid = local_client.post("/runs", json={}).json()["run_id"]
    local_client.put(f"/vfs/{rid}/design/icon.png",
                     json={"content": base64.b64encode(raw).decode(),
                           "mime": "image/png", "content_encoding": "base64"})
    r = local_client.get(f"/vfs/{rid}/design/icon.png")
    assert r.status_code == 200
    assert r.content == raw
    assert r.headers["content-type"] == "image/png"


def test_usage_empty_log_exact_total_keyset(local_client):
    rid = local_client.post("/runs", json={}).json()["run_id"]
    r = local_client.get(f"/runs/{rid}/usage")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"total", "by_step", "entries"}
    assert set(body["total"].keys()) == {
        "input_tokens", "output_tokens", "images", "cost_usd", "calls"}
    assert body["entries"] == []


def test_gallery_exact_keysets(local_client):
    rid = local_client.post("/runs", json={"title": "G"}).json()["run_id"]
    r = local_client.get(f"/runs/{rid}/gallery")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"run", "sections"}
    assert body["sections"]
    assert set(body["sections"][0].keys()) == {
        "studio", "label", "status", "has_preview", "groups"}


def test_preview_returns_html(local_client):
    rid = local_client.post("/runs", json={}).json()["run_id"]
    r = local_client.get(f"/runs/{rid}/preview")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
