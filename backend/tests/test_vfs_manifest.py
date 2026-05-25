import pytest

from app.vfs.local import LocalVfsStore


@pytest.fixture()
def store(tmp_path):
    return LocalVfsStore(storage_dir=str(tmp_path))


def test_patch_manifest_updates_fields_and_timestamp(store):
    m0 = store.create_run("r1", title="A")
    m1 = store.patch_manifest("r1", {"title": "B", "languages": ["ko", "vi"]})
    assert m1.title == "B"
    assert m1.languages == ["ko", "vi"]
    assert m1.updated_at >= m0.updated_at


def test_set_step_status_records_and_advances_current_step(store):
    store.create_run("r1")
    m = store.set_step_status("r1", "brainstorming", "done")
    assert m.step_status["brainstorming"] == "done"
    assert m.current_step == "brainstorming"   # 불변식: 스텝전환 → current_step 동기


def test_set_step_status_rejects_unknown_step(store):
    store.create_run("r1")
    with pytest.raises(ValueError):
        store.set_step_status("r1", "marketing", "done")


def test_manifest_ops_require_existing_run(store):
    with pytest.raises(KeyError):
        store.patch_manifest("ghost", {"title": "x"})
