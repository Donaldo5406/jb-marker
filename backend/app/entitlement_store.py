"""EntitlementStore — dev_pass 영속 (Local 인메모리 / Supabase profiles)."""
from __future__ import annotations

from abc import ABC, abstractmethod


class EntitlementStore(ABC):
    @abstractmethod
    def check(self, user_id: str) -> bool: ...
    @abstractmethod
    def set_dev_pass(self, user_id: str) -> None: ...
    @abstractmethod
    def reset(self, user_id: str | None = None) -> None: ...


class LocalEntitlementStore(EntitlementStore):
    def __init__(self) -> None:
        self._dev: dict[str, bool] = {}

    def check(self, user_id):
        return self._dev.get(user_id, False)

    def set_dev_pass(self, user_id):
        self._dev[user_id] = True

    def reset(self, user_id=None):
        if user_id is None:
            self._dev.clear()
        else:
            self._dev.pop(user_id, None)


class SupabaseEntitlementStore(EntitlementStore):
    def __init__(self, settings) -> None:
        from .supabase_client import build_service_client
        self._sb = build_service_client(settings)

    def check(self, user_id):
        res = (self._sb.table("profiles").select("entitled")
               .eq("user_id", user_id).limit(1).execute())
        return bool(res.data and res.data[0].get("entitled"))

    def set_dev_pass(self, user_id):
        self._sb.table("profiles").upsert(
            {"user_id": user_id, "entitled": True}, on_conflict="user_id").execute()

    def reset(self, user_id=None):
        q = self._sb.table("profiles").update({"entitled": False})
        if user_id is not None:
            q = q.eq("user_id", user_id)
        else:
            q = q.neq("user_id", "")  # 전체
        q.execute()


def get_entitlement_store(settings) -> EntitlementStore:
    if settings.vfs_backend == "supabase":
        return SupabaseEntitlementStore(settings)
    return LocalEntitlementStore()
