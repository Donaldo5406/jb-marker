from app.session.record import (
    SessionRecord, derive_session_id, session_path,
    STATUS_ACTIVE,
)


def test_new_sets_created_equals_updated_and_active():
    rec = SessionRecord.new("run_42", "design", now_ms=1000)
    assert rec.created_at_ms == 1000
    assert rec.updated_at_ms == 1000
    assert rec.status == STATUS_ACTIVE
    assert rec.suspended_at_ms is None


def test_derive_session_id_is_deterministic():
    assert derive_session_id("run_42", "design") == "sess_run_42_design"


def test_session_path_is_per_studio_namespace():
    assert session_path("run_42", "review") == "/run_42/review/_session.json"


def test_json_round_trip_preserves_fields():
    rec = SessionRecord.new("r", "brainstorming", now_ms=5)
    rec.updated_at_ms = 9
    rec.last_activity_kind = "resume"
    back = SessionRecord.from_json(rec.to_json())
    assert back == rec


def test_to_json_includes_derived_session_id():
    import json
    rec = SessionRecord.new("r", "deploy", now_ms=1)
    assert json.loads(rec.to_json())["session_id"] == "sess_r_deploy"
