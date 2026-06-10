"""gateway/state — _state.json 공용 I/O 계약 (경로·source·mime·version)."""
import json

from app.gateway.state import STATE_VERSION, load_state, save_state, state_path
from app.vfs.local import LocalVfsStore


def _store(tmp_path):
    s = LocalVfsStore(storage_dir=str(tmp_path))
    s.create_run("r1")
    return s


def test_state_path_convention():
    assert state_path("r1", "design") == "/r1/design/_state.json"


def test_load_missing_returns_default(tmp_path):
    s = _store(tmp_path)
    st = load_state(s, "r1", "design", default_factory=lambda: {"step": "S0"})
    assert st == {"step": "S0"}


def test_save_adds_version_and_roundtrips(tmp_path):
    s = _store(tmp_path)
    save_state(s, "r1", "review", {"step": "R1"})
    node = s.get("/r1/review/_state.json")
    assert node.source == "marker" and node.mime == "application/json"
    data = json.loads(node.content_text)
    assert data["version"] == STATE_VERSION and data["step"] == "R1"
    st = load_state(s, "r1", "review", default_factory=dict)
    assert st["version"] == STATE_VERSION


def test_save_preserves_existing_version(tmp_path):
    s = _store(tmp_path)
    save_state(s, "r1", "design", {"step": "S1", "version": 99})
    assert json.loads(s.get("/r1/design/_state.json").content_text)["version"] == 99
