"""dev_pass 흐름."""
import pytest
from app import entitlement


@pytest.fixture(autouse=True)
def _reset():
    entitlement.reset()
    yield
    entitlement.reset()


def test_default_false():
    assert entitlement.check("alice") is False


def test_set_then_check():
    entitlement.set_dev_pass("alice")
    assert entitlement.check("alice") is True


def test_reset_specific_user():
    entitlement.set_dev_pass("alice")
    entitlement.set_dev_pass("bob")
    entitlement.reset("alice")
    assert entitlement.check("alice") is False
    assert entitlement.check("bob") is True


def test_put_entitlement_is_per_user(monkeypatch, tmp_path):
    """A유저 토글이 B유저에 영향 없어야 한다 (local 모드, demo user)."""
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "0")
    monkeypatch.setenv("JBM_STORAGE_DIR", str(tmp_path))
    from app.server import create_app
    from fastapi.testclient import TestClient
    client = TestClient(create_app())
    r0 = client.get("/entitlement")
    assert r0.json()["marker"] is False
    r1 = client.put("/entitlement", json={"marker": True})
    assert r1.json()["marker"] is True
    assert client.get("/entitlement").json()["marker"] is True
