"""History gallery 집계 — build_gallery 순수 함수 계약."""
from app.history.gallery import build_gallery
from app.vfs.types import Manifest, VfsNode


def _man(**kw) -> Manifest:
    base = dict(run_id="r1", user_id="u1", title="T", current_step="design",
                step_status={"brainstorming": "done", "design": "active"},
                languages=["ko", "vi"], created_at="2026-05-29T00:00:00Z")
    base.update(kw)
    return Manifest(**base)


def _node(path, mime=None) -> VfsNode:
    return VfsNode(run_id="r1", path=path, mime=mime)


def test_sections_are_four_studios_in_fixed_order():
    out = build_gallery(_man(), [])
    assert [s["studio"] for s in out["sections"]] == \
        ["brainstorming", "design", "review", "deploy"]
    assert [s["label"] for s in out["sections"]] == ["기획", "디자인", "검토", "배포"]


def test_run_meta_exposed():
    out = build_gallery(_man(), [])
    assert out["run"]["run_id"] == "r1"
    assert out["run"]["languages"] == ["ko", "vi"]
    assert out["run"]["step_status"]["design"] == "active"


def test_status_from_step_status_or_none():
    out = build_gallery(_man(), [])
    by = {s["studio"]: s for s in out["sections"]}
    assert by["brainstorming"]["status"] == "done"
    assert by["review"]["status"] == "none"  # step_status에 없음


def test_node_grouped_into_its_studio_section():
    nodes = [_node("/r1/brainstorming/spec.md", "text/markdown")]
    out = build_gallery(_man(), nodes)
    by = {s["studio"]: s for s in out["sections"]}
    items = [i for g in by["brainstorming"]["groups"] for i in g["items"]]
    assert any(i["name"] == "spec.md" for i in items)


def test_kind_classification():
    nodes = [
        _node("/r1/brainstorming/spec.md", "text/markdown"),
        _node("/r1/design/design-system/components/visual/v1.png", "image/png"),
        _node("/r1/design/final/ko/main.scene", "application/json"),
    ]
    out = build_gallery(_man(), nodes)
    kinds = {i["name"]: g["kind"]
             for s in out["sections"] for g in s["groups"] for i in g["items"]}
    assert kinds["spec.md"] == "document"
    assert kinds["v1.png"] == "image"
    assert kinds["main.scene"] == "scene"


def test_underscore_nodes_hidden():
    nodes = [
        _node("/r1/design/_state.json", "application/json"),
        _node("/r1/design/_render/ko.png", "image/png"),
        _node("/r1/design/design-system/tokens.json", "application/json"),
    ]
    out = build_gallery(_man(), nodes)
    names = [i["name"] for s in out["sections"] for g in s["groups"] for i in g["items"]]
    assert "tokens.json" in names
    assert "_state.json" not in names
    assert "ko.png" not in names  # _render/ 하위


def test_non_studio_nodes_excluded():
    nodes = [
        _node("/r1/manifest.json", "application/json"),  # 루트
        _node("/r1/usage/log.jsonl", "application/json"),  # 비-산출물 스튜디오
        _node("/r1/brainstorming/spec.md", "text/markdown"),
    ]
    out = build_gallery(_man(), nodes)
    names = [i["name"] for s in out["sections"] for g in s["groups"] for i in g["items"]]
    assert "spec.md" in names
    assert "manifest.json" not in names
    assert "log.jsonl" not in names


def test_has_preview_only_when_design_tokens_present():
    nodes = [_node("/r1/design/design-system/tokens.json", "application/json")]
    out = build_gallery(_man(), nodes)
    by = {s["studio"]: s for s in out["sections"]}
    assert by["design"]["has_preview"] is True
    assert by["brainstorming"]["has_preview"] is False


def test_is_media_flag():
    nodes = [
        _node("/r1/design/design-system/components/visual/v1.png", "image/png"),
        _node("/r1/brainstorming/spec.md", "text/markdown"),
    ]
    out = build_gallery(_man(), nodes)
    flags = {i["name"]: i["is_media"]
             for s in out["sections"] for g in s["groups"] for i in g["items"]}
    assert flags["v1.png"] is True
    assert flags["spec.md"] is False


# --- 라우트 통합 ---
from fastapi.testclient import TestClient
from app.server import create_app


def _client():
    return TestClient(create_app())


def test_gallery_route_empty_run_returns_four_sections():
    c = _client()
    run_id = c.post("/runs", json={"title": "n"}).json()["run_id"]
    r = c.get(f"/runs/{run_id}/gallery")
    assert r.status_code == 200
    body = r.json()
    assert [s["studio"] for s in body["sections"]] == \
        ["brainstorming", "design", "review", "deploy"]
    assert body["run"]["run_id"] == run_id


def test_gallery_route_reflects_put_artifact():
    c = _client()
    run_id = c.post("/runs", json={"title": "n"}).json()["run_id"]
    c.put(f"/vfs/{run_id}/brainstorming/spec.md",
          json={"content": "# spec", "mime": "text/markdown"})
    body = c.get(f"/runs/{run_id}/gallery").json()
    by = {s["studio"]: s for s in body["sections"]}
    names = [i["name"] for g in by["brainstorming"]["groups"] for i in g["items"]]
    assert "spec.md" in names


def test_gallery_route_404_for_missing_run():
    c = _client()
    r = c.get("/runs/nope/gallery")
    assert r.status_code == 404
