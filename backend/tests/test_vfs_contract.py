# backend/tests/test_vfs_contract.py
"""Local/Supabase 공유 계약. Supabase는 SUPABASE_TEST=1 + 키 있을 때만."""
from __future__ import annotations

import os
import uuid

import pytest

from app.vfs.local import LocalVfsStore


def _supabase_store():
    from dataclasses import replace
    from app.config import load_settings
    from app.vfs.supabase import SupabaseVfsStore
    s = load_settings()
    s = replace(s, vfs_backend="supabase")
    return SupabaseVfsStore(s)


@pytest.fixture(params=["local", "supabase"])
def store(request, tmp_path):
    if request.param == "local":
        return LocalVfsStore(storage_dir=str(tmp_path))
    if os.getenv("SUPABASE_TEST") != "1":
        pytest.skip("SUPABASE_TEST!=1 — Supabase 계약 테스트 스킵")
    return _supabase_store()


@pytest.fixture()
def run_id(store):
    rid = uuid.uuid4().hex[:12]
    # Supabase는 FK 위해 user_id 필요(uuid 형식). Local은 무관.
    store.create_run(rid, user_id="00000000-0000-0000-0000-000000000000", title="t")
    yield rid
    # 정리: Supabase면 run 삭제(cascade로 노드 제거). Local은 GC.
    try:
        store._sb.table("runs").delete().eq("run_id", rid).execute()  # type: ignore[attr-defined]
    except AttributeError:
        pass


def test_text_put_get_roundtrip(store, run_id):
    store.put(f"/{run_id}/brainstorming/spec.md", "# spec", source="marker", mime="text/markdown")
    n = store.get(f"/{run_id}/brainstorming/spec.md")
    assert n is not None and n.content_text == "# spec"
    assert n.hash is not None


def test_blob_put_get_roundtrip(store, run_id):
    png = b"\x89PNG\r\n\x1a\n" + b"x" * 32
    store.put(f"/{run_id}/design/visual.png", png, source="gemini", mime="image/png")
    n = store.get(f"/{run_id}/design/visual.png")
    assert n is not None and n.blob == png
    assert n.meta.get("type") == "image"  # 불변식: 미디어 put → meta 동시기록


def test_list_prefix(store, run_id):
    store.put(f"/{run_id}/brainstorming/a.md", "a", mime="text/markdown")
    store.put(f"/{run_id}/brainstorming/b.md", "b", mime="text/markdown")
    store.put(f"/{run_id}/design/c.md", "c", mime="text/markdown")
    bs = store.list(f"/{run_id}/brainstorming")
    paths = sorted(n.path for n in bs)
    assert paths == [f"/{run_id}/brainstorming/a.md", f"/{run_id}/brainstorming/b.md"]


def test_manifest_step_status(store, run_id):
    m = store.set_step_status(run_id, "brainstorming", "done")
    assert m.step_status["brainstorming"] == "done"
    assert m.current_step == "brainstorming"


def test_list_runs_filters_user(store):
    u = "00000000-0000-0000-0000-0000000000aa"
    rid = uuid.uuid4().hex[:12]
    store.create_run(rid, user_id=u, title="mine")
    try:
        mine = store.list_runs(user_id=u)
        assert any(m.run_id == rid for m in mine)
    finally:
        try:
            store._sb.table("runs").delete().eq("run_id", rid).execute()  # type: ignore[attr-defined]
        except AttributeError:
            pass
