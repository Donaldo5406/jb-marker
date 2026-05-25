import pytest

from app.gateway.entitlement import EntitlementError, check_entitlement


def test_free_tier_allows_raw():
    check_entitlement(is_marker=False, override=False)   # no raise


def test_free_tier_blocks_marker():
    with pytest.raises(EntitlementError):
        check_entitlement(is_marker=True, override=False)


def test_override_allows_marker():
    check_entitlement(is_marker=True, override=True)      # no raise
