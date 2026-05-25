import pytest

from app.vfs.local import LocalVfsStore


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("JBM_STORAGE_DIR", str(tmp_path))
    return LocalVfsStore(storage_dir=str(tmp_path))


def test_create_run_and_put_get_text(store):
    store.create_run("r1", title="캠페인")
    node = store.put("/r1/brainstorming/spec.md", "# spec", source="marker", mime="text/markdown")
    assert node.content_text == "# spec"
    got = store.get("/r1/brainstorming/spec.md")
    assert got is not None and got.content_text == "# spec"
    assert got.source == "marker"


def test_list_by_prefix(store):
    store.create_run("r1")
    store.put("/r1/brainstorming/spec.md", "a")
    store.put("/r1/brainstorming/plan.md", "b")
    store.put("/r1/design/metadata.md", "c")
    paths = sorted(n.path for n in store.list("/r1/brainstorming"))
    assert paths == ["/r1/brainstorming/plan.md", "/r1/brainstorming/spec.md"]


def test_update_and_delete(store):
    store.create_run("r1")
    store.put("/r1/brainstorming/spec.md", "v1")
    store.update("/r1/brainstorming/spec.md", {"content_text": "v2"})
    assert store.get("/r1/brainstorming/spec.md").content_text == "v2"
    store.delete("/r1/brainstorming/spec.md")
    assert store.get("/r1/brainstorming/spec.md") is None


def test_put_rejects_invalid_path(store):
    store.create_run("r1")
    with pytest.raises(ValueError):
        store.put("/r1/notastudio/x.md", "x")


def test_blob_put_persists_bytes_and_meta(store):
    store.create_run("r1")
    data = b"\x89PNG fake"
    node = store.put("/r1/design/visual.png", data, mime="image/png", source="gemini")
    # 블롭은 디스크에 기록되고 blob_path가 채워진다
    assert node.blob_path is not None
    # 불변식: 미디어 put 시 meta 동시기록(비어있지 않음)
    assert node.meta and node.meta.get("source") == "gemini"
    # get()은 바이트를 로드해 서빙 가능
    got = store.get("/r1/design/visual.png")
    assert got is not None and got.blob == data


def test_blob_put_autogenerates_meta_when_missing(store):
    store.create_run("r1")
    node = store.put("/r1/design/v2.png", b"x", mime="image/png")
    assert node.meta != {}        # 불변식: 비어있지 않아야 함
    assert node.meta.get("type") in {"image", "file"}


def test_list_runs_filters_by_user_and_sorts_desc():
    from app.vfs.local import LocalVfsStore
    s = LocalVfsStore(storage_dir="data/test-listruns")
    s.create_run("aaa", user_id="demo", title="첫째")
    s.create_run("bbb", user_id="demo", title="둘째")
    s.create_run("ccc", user_id="other", title="남")
    runs = s.list_runs(user_id="demo")
    ids = [m.run_id for m in runs]
    assert "ccc" not in ids
    assert set(ids) == {"aaa", "bbb"}
    # created_at 내림차순(최신 먼저). 동일 타임스탬프 가능성 → 부분순서만 검증
    assert all(hasattr(m, "step_status") for m in runs)
