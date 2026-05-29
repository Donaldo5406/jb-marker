"""entitlement — EntitlementStore 위임. 기본 Local 싱글턴(테스트·오프라인).

server.create_app이 supabase 모드면 set_store()로 교체.
"""
from __future__ import annotations

from .entitlement_store import EntitlementStore, LocalEntitlementStore

_store: EntitlementStore = LocalEntitlementStore()


def set_store(store: EntitlementStore) -> None:
    global _store
    _store = store


def check(user_id: str) -> bool:
    return _store.check(user_id)


def set_dev_pass(user_id: str) -> None:
    _store.set_dev_pass(user_id)


def reset(user_id: str | None = None) -> None:
    _store.reset(user_id)
