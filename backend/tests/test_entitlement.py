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
