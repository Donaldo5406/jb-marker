"""인메모리 entitlement — dev_pass(데모 결제 통과 플래그). M7에서 Supabase 컬럼으로 전환."""
from __future__ import annotations

_DEV_PASS: dict[str, bool] = {}


def check(user_id: str) -> bool:
    return _DEV_PASS.get(user_id, False)


def set_dev_pass(user_id: str) -> None:
    _DEV_PASS[user_id] = True


def reset(user_id: str | None = None) -> None:
    """테스트용 — 특정 user 또는 전체 초기화."""
    if user_id is None:
        _DEV_PASS.clear()
    else:
        _DEV_PASS.pop(user_id, None)
