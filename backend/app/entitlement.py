"""entitlement — EntitlementStore 위임. 기본 Local 싱글턴(테스트·오프라인).

server.create_app이 supabase 모드면 set_store()로 교체.
override 포함 단일 판정은 is_entitled() 하나만 사용한다.
"""
from __future__ import annotations

from typing import Callable

from .entitlement_store import EntitlementStore, LocalEntitlementStore

_store: EntitlementStore = LocalEntitlementStore()

_override_source: "Callable[[], bool] | None" = None


def set_store(store: EntitlementStore) -> None:
    global _store
    _store = store


def set_override_source(fn: "Callable[[], bool] | None") -> None:
    """env override 공급자 등록(create_app가 settings로 주입). None=해제."""
    global _override_source
    _override_source = fn


def is_entitled(user_id: str) -> bool:
    """단일 choke 판정 — env override OR 사용자 entitlement (Refactor C4, spec §7-1).

    gateway·advisor chat·dispatch·GET/PUT /entitlement·deploy _state 전원이
    이 함수 하나만 호출한다.
    """
    if _override_source is not None and bool(_override_source()):
        return True
    return _store.check(user_id)


# 주의: check()는 store 단독 판정(override 미반영) — 신규 코드는 is_entitled()를 사용할 것.
def check(user_id: str) -> bool:
    return _store.check(user_id)


def set_dev_pass(user_id: str) -> None:
    _store.set_dev_pass(user_id)


def reset(user_id: str | None = None) -> None:
    _store.reset(user_id)
