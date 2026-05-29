"""로컬 모드에서는 user_id="demo" 단일 → 가드 통과. supabase 교차사용자 404는
계약 테스트(게이트)에서. 여기선 가드 함수 자체의 단위 동작을 검증."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.vfs.local import LocalVfsStore
from app.server import _require_run_owner_factory


def test_owner_guard_passes_for_owner(tmp_path):
    store = LocalVfsStore(storage_dir=str(tmp_path))
    store.create_run("r1", user_id="alice")
    guard = _require_run_owner_factory(store)
    guard("r1", "alice")  # 예외 없음


def test_owner_guard_404_for_other_user(tmp_path):
    store = LocalVfsStore(storage_dir=str(tmp_path))
    store.create_run("r1", user_id="alice")
    guard = _require_run_owner_factory(store)
    with pytest.raises(HTTPException) as ei:
        guard("r1", "bob")
    assert ei.value.status_code == 404


def test_owner_guard_404_for_missing_run(tmp_path):
    store = LocalVfsStore(storage_dir=str(tmp_path))
    guard = _require_run_owner_factory(store)
    with pytest.raises(HTTPException) as ei:
        guard("ghost", "alice")
    assert ei.value.status_code == 404
