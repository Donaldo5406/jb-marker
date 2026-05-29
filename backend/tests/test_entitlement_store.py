from __future__ import annotations

from app.entitlement_store import LocalEntitlementStore


def test_local_default_false():
    s = LocalEntitlementStore()
    assert s.check("alice") is False


def test_local_set_then_check():
    s = LocalEntitlementStore()
    s.set_dev_pass("alice")
    assert s.check("alice") is True


def test_local_reset():
    s = LocalEntitlementStore()
    s.set_dev_pass("alice")
    s.reset("alice")
    assert s.check("alice") is False
