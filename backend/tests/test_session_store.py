from app.vfs.local import LocalVfsStore
from app.session.store import SessionStore
from app.session.record import (
    session_path, STATUS_ACTIVE, STATUS_SUSPENDED, STATUS_ARCHIVED,
)
from app.session.liveness import Thresholds

TH = Thresholds(stall_ms=900_000, suspend_ms=3_600_000, retention_ms=604_800_000)


def _vfs(tmp_path):
    s = LocalVfsStore(storage_dir=str(tmp_path))
    s.create_run("r1", languages=["ko"])
    return s


def test_get_or_create_persists_session_json(tmp_path):
    vfs = _vfs(tmp_path)
    ss = SessionStore(vfs, TH)
    rec = ss.get_or_create("r1", "design", now_ms=1000)
    assert rec.created_at_ms == 1000 and rec.status == STATUS_ACTIVE
    node = vfs.get(session_path("r1", "design"))
    assert node is not None and node.content_text  # 영속됨


def test_get_or_create_is_idempotent(tmp_path):
    vfs = _vfs(tmp_path)
    ss = SessionStore(vfs, TH)
    a = ss.get_or_create("r1", "design", now_ms=1000)
    b = ss.get_or_create("r1", "design", now_ms=9999)  # 두 번째는 기존 로드
    assert b.created_at_ms == 1000  # 재생성 안 함


def test_touch_updates_updated_at_and_reactivates(tmp_path):
    vfs = _vfs(tmp_path)
    ss = SessionStore(vfs, TH)
    ss.get_or_create("r1", "design", now_ms=0)
    rec = ss.touch("r1", "design", now_ms=5000, kind="user_turn")
    assert rec.updated_at_ms == 5000
    assert rec.status == STATUS_ACTIVE
    assert rec.last_activity_kind == "user_turn"


def test_heartbeat_on_missing_returns_exists_false(tmp_path):
    ss = SessionStore(_vfs(tmp_path), TH)
    out = ss.heartbeat("r1", "design", now_ms=0)
    assert out == {"kind": "heartbeat", "exists": False, "status": None, "resumable": False}


def test_heartbeat_active_session(tmp_path):
    ss = SessionStore(_vfs(tmp_path), TH)
    ss.get_or_create("r1", "design", now_ms=0)
    out = ss.heartbeat("r1", "design", now_ms=10)
    assert out["kind"] == "heartbeat"
    assert out["exists"] is True
    assert out["liveness"] == "healthy"
    assert out["resumable"] is True


def test_heartbeat_persists_lazy_suspend_transition(tmp_path):
    vfs = _vfs(tmp_path)
    ss = SessionStore(vfs, TH)
    ss.get_or_create("r1", "design", now_ms=0)
    ss.heartbeat("r1", "design", now_ms=3_600_000)  # idle≥suspend
    # 디스크에서 다시 로드해도 suspended (영속됨)
    reloaded = SessionStore(vfs, TH)._load("r1", "design")
    assert reloaded.status == STATUS_SUSPENDED


def test_list_returns_all_studios_with_lifecycle(tmp_path):
    vfs = _vfs(tmp_path)
    ss = SessionStore(vfs, TH)
    ss.get_or_create("r1", "brainstorming", now_ms=0)
    ss.get_or_create("r1", "design", now_ms=100)
    out = ss.list("r1", now_ms=200)
    assert out["kind"] == "session_list"
    studios = {s["studio"] for s in out["sessions"]}
    assert studios == {"brainstorming", "design"}  # review/deploy 미생성 → 제외


def test_resume_missing_returns_expired(tmp_path):
    ss = SessionStore(_vfs(tmp_path), TH)
    out = ss.resume("r1", "design", now_ms=0)
    assert out == {"kind": "expired", "reason": "no_session"}


def test_resume_suspended_within_retention_restores_active(tmp_path):
    vfs = _vfs(tmp_path)
    ss = SessionStore(vfs, TH)
    ss.get_or_create("r1", "design", now_ms=0)
    out = ss.resume("r1", "design", now_ms=3_600_000)  # 60m idle → suspended였다가 resume
    assert out["kind"] == "restored"
    assert out["status"] == "active"
    assert ss._load("r1", "design").status == STATUS_ACTIVE


def test_resume_archived_returns_expired(tmp_path):
    vfs = _vfs(tmp_path)
    ss = SessionStore(vfs, TH)
    ss.get_or_create("r1", "design", now_ms=0)
    out = ss.resume("r1", "design", now_ms=604_800_001)  # retention 초과
    assert out["kind"] == "expired"
    assert out["reason"] == "retention_elapsed"
    assert ss._load("r1", "design").status == STATUS_ARCHIVED  # 영속


def test_suspend_marks_suspended(tmp_path):
    vfs = _vfs(tmp_path)
    ss = SessionStore(vfs, TH)
    ss.get_or_create("r1", "design", now_ms=0)
    out = ss.suspend("r1", "design", now_ms=5000)
    assert out == {"kind": "suspended", "status": STATUS_SUSPENDED}
    assert ss._load("r1", "design").suspended_at_ms == 5000


def test_studio_sessions_are_isolated(tmp_path):
    # spec §4: 한 스튜디오 전이가 다른 스튜디오 세션을 건드리지 않음(구조적 독립)
    vfs = _vfs(tmp_path)
    ss = SessionStore(vfs, TH)
    ss.get_or_create("r1", "design", now_ms=0)
    ss.get_or_create("r1", "review", now_ms=0)
    ss.suspend("r1", "design", now_ms=5000)
    assert ss._load("r1", "design").status == STATUS_SUSPENDED
    assert ss._load("r1", "review").status == STATUS_ACTIVE  # 영향 없음


def test_settings_expose_session_thresholds_with_defaults(monkeypatch):
    monkeypatch.delenv("SESSION_STALL_MS", raising=False)
    monkeypatch.delenv("SESSION_SUSPEND_MS", raising=False)
    monkeypatch.delenv("SESSION_RETENTION_MS", raising=False)
    from app.config import load_settings
    s = load_settings()
    assert s.session_stall_ms == 900_000
    assert s.session_suspend_ms == 3_600_000
    assert s.session_retention_ms == 604_800_000


def test_settings_session_thresholds_env_override(monkeypatch):
    monkeypatch.setenv("SESSION_SUSPEND_MS", "120000")
    from app.config import load_settings
    assert load_settings().session_suspend_ms == 120_000
