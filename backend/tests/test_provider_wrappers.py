"""providers/wrappers — server.py 클로저에서 추출된 래퍼의 계약 (P4 T1)."""
from app.config import load_settings
from app.providers.base import Message
from app.providers.wrappers import ModelBoundProvider, TrackedProvider


def _settings(monkeypatch):
    monkeypatch.setenv("VFS_BACKEND", "local")
    return load_settings()


def test_model_bound_provider_has_name_and_binds_model(monkeypatch):
    s = _settings(monkeypatch)
    p = ModelBoundProvider("fake", s)
    assert p.name == "fake"          # legal_search가 .name 검사
    assert p._model == "fake-1"
    assert hasattr(p, "review_image") and hasattr(p, "generate_image")
    # complete는 호출자 model 인자를 무시하고 바인딩 모델 강제
    resp = p.complete([Message(role="user", content="hi")], model="ignored")
    assert resp is not None
    assert resp.model == "fake-1"


def test_tracked_provider_records_image_usage(monkeypatch, tmp_path):
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("JBM_STORAGE_DIR", str(tmp_path))
    from app.vfs.factory import get_vfs_store
    from app.observability import usage as usage_log
    s = load_settings()
    store = get_vfs_store(s)
    store.create_run("r1", user_id="demo", title=None, languages=[])
    inner = ModelBoundProvider("fake", s)
    tp = TrackedProvider(inner, store=store, run_id="r1", step="design", settings=s)
    assert tp.name == "fake"
    tp.generate_image("a poster")
    entries = usage_log.read_log(store, run_id="r1")
    assert any(e.get("kind") == "image" for e in entries)
