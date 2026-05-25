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
