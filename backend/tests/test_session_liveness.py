from app.session.record import (
    SessionRecord, STATUS_ACTIVE, STATUS_SUSPENDED, STATUS_ARCHIVED,
)
from app.session.liveness import (
    Thresholds, evaluate, heartbeat_view,
    HEALTHY, STALLED, SUSPENDED, ARCHIVED, TRANSPORT_DEAD,
)

TH = Thresholds(stall_ms=900_000, suspend_ms=3_600_000, retention_ms=604_800_000)


def _rec(updated_at_ms, status=STATUS_ACTIVE, suspended_at_ms=None):
    return SessionRecord(run_id="r", studio="design", created_at_ms=0,
                         updated_at_ms=updated_at_ms, status=status,
                         suspended_at_ms=suspended_at_ms)


def test_active_when_idle_below_stall():
    rec = _rec(0)
    assert evaluate(rec, now_ms=899_999, th=TH) == HEALTHY
    assert rec.status == STATUS_ACTIVE


def test_stalled_at_stall_boundary_is_non_persistent():
    rec = _rec(0)
    assert evaluate(rec, now_ms=900_000, th=TH) == STALLED
    assert rec.status == STATUS_ACTIVE  # 경고는 파생, status 미변경


def test_suspends_at_suspend_boundary_and_persists_status():
    rec = _rec(0)
    assert evaluate(rec, now_ms=3_600_000, th=TH) == SUSPENDED
    assert rec.status == STATUS_SUSPENDED
    assert rec.suspended_at_ms == 0  # = updated_at_ms(마지막 활동)


def test_cascades_active_to_archived_in_one_call():
    # 마지막 활동 후 retention+suspend 초과 → 단일 호출에서 archived까지
    rec = _rec(0)
    assert evaluate(rec, now_ms=604_800_001, th=TH) == ARCHIVED
    assert rec.status == STATUS_ARCHIVED


def test_suspended_stays_suspended_within_retention():
    rec = _rec(0, status=STATUS_SUSPENDED, suspended_at_ms=0)
    assert evaluate(rec, now_ms=604_799_999, th=TH) == SUSPENDED
    assert rec.status == STATUS_SUSPENDED


def test_suspended_to_archived_after_retention():
    rec = _rec(0, status=STATUS_SUSPENDED, suspended_at_ms=0)
    assert evaluate(rec, now_ms=604_800_000, th=TH) == ARCHIVED
    assert rec.status == STATUS_ARCHIVED


def test_transport_dead_overrides():
    rec = _rec(0)
    assert evaluate(rec, now_ms=10, th=TH, transport_alive=False) == TRANSPORT_DEAD


def test_clock_skew_negative_idle_is_active():
    rec = _rec(1000)
    assert evaluate(rec, now_ms=500, th=TH) == HEALTHY  # saturating_sub


def test_heartbeat_view_exposes_warn_suspend_expires():
    rec = _rec(0, status=STATUS_SUSPENDED, suspended_at_ms=0)
    view = heartbeat_view(rec, now_ms=10, th=TH)
    assert view["liveness"] == SUSPENDED
    assert view["warn_at"] == 900_000
    assert view["suspend_at"] == 3_600_000
    assert view["expires_at"] == 604_800_000
