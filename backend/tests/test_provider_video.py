"""Provider.generate_video 계약 테스트 (영상 액터 — video-harness spec §4)."""
import pytest

from app.providers.base import Provider
from app.providers.fake import FakeProvider
from app.providers.demo import DemoProvider


def test_base_generate_video_not_implemented():
    class Bare(Provider):
        def complete(self, messages, *, model=None, system=None, tools=None, **kw): ...

    with pytest.raises(NotImplementedError):
        Bare().generate_video("배경 footage", aspect="9:16")


def test_fake_generate_video_returns_bytes():
    out = FakeProvider().generate_video("추상 금융 배경", aspect="9:16",
                                        duration_sec=15, fps=30)
    assert isinstance(out, bytes) and len(out) > 0


def test_demo_generate_video_returns_real_mp4():
    """demo footage = 실 Veo 광고영상(mp4) — Veo 크레딧 없이도 진짜 광고물 렌더."""
    out = DemoProvider().generate_video("추상 금융 배경", aspect="9:16")
    assert isinstance(out, bytes) and len(out) > 100_000   # 실 영상(>100KB)
    assert b"ftyp" in out[:32]                             # mp4 시그니처


def test_load_demo_video_is_mp4():
    from app.providers import demo_fixtures as F
    out = F.load_demo_video()
    assert isinstance(out, bytes) and b"ftyp" in out[:32]


def _fake_genai_video(captured: dict):
    """genai.Client(...).models.generate_videos를 가로채 config 기록 + 완료 operation 반환."""
    class _Vid:
        video_bytes = b"\x00\x00\x00\x18ftypmp42_vid"

    class _GenVid:
        video = _Vid()

    class _Resp:
        generated_videos = [_GenVid()]

    class _Op:
        done = True
        response = _Resp()

    class _Models:
        def generate_videos(self, *, model, prompt, config=None):
            captured["model"] = model
            captured["config"] = config
            captured["prompt"] = prompt
            return _Op()

    class _Client:
        def __init__(self, *a, **k):
            self.models = _Models()

    import types as _t
    return _t.SimpleNamespace(Client=_Client)


def test_google_generate_video_returns_bytes_and_passes_aspect(monkeypatch):
    genai = pytest.importorskip("google.genai")
    from google.genai import types
    from app.providers.google_client import GoogleProvider
    captured: dict = {}
    monkeypatch.setattr(genai, "Client", _fake_genai_video(captured).Client)
    # config 클래스 시그니처는 SDK 버전 의존 → fake로 치환해 래퍼 로직만 검증
    monkeypatch.setattr(types, "GenerateVideosConfig",
                        lambda **kw: {"video_cfg": kw}, raising=False)
    out = GoogleProvider("k").generate_video("프리미엄 금융 배경", aspect="9:16",
                                             duration_sec=8, fps=30)
    assert out == b"\x00\x00\x00\x18ftypmp42_vid"
    cfg = captured["config"]["video_cfg"]
    assert cfg["aspect_ratio"] == "9:16"
    # 화면·외국어 글자 억제: negative_prompt(억제어) + 결정론 seed
    assert "글자" in cfg["negative_prompt"] and "텍스트" in cfg["negative_prompt"]
    assert isinstance(cfg["seed"], int)
    assert "글자" in captured["prompt"]   # 프롬프트 no-text 지시도 유지


def test_google_generate_video_omits_config_for_unsupported_aspect(monkeypatch):
    genai = pytest.importorskip("google.genai")
    from app.providers.google_client import GoogleProvider
    captured: dict = {}
    monkeypatch.setattr(genai, "Client", _fake_genai_video(captured).Client)
    GoogleProvider("k").generate_video("배경", aspect="7:13")
    assert captured["config"] is None


def test_google_generate_video_downloads_uri_when_bytes_empty(monkeypatch):
    """Veo가 영상을 video_bytes 대신 uri로 반환할 때 files.download로 바이트를 채운다."""
    genai = pytest.importorskip("google.genai")
    from google.genai import types
    from app.providers.google_client import GoogleProvider
    called = {}

    class _Vid:
        video_bytes = b""           # 비어 옴(실제 Veo 응답)
        uri = "https://generativelanguage.googleapis.com/v1beta/files/x:download"

    class _GenVid:
        video = _Vid()

    class _Resp:
        generated_videos = [_GenVid()]

    class _Op:
        done = True
        response = _Resp()

    class _Files:
        def download(self, *, file):
            file.video_bytes = b"REAL_VEO_VIDEO_BYTES"
            called["download"] = True

    class _Models:
        def generate_videos(self, *, model, prompt, config=None):
            return _Op()

    class _Client:
        def __init__(self, *a, **k):
            self.models = _Models()
            self.files = _Files()

    monkeypatch.setattr(genai, "Client", _Client)
    monkeypatch.setattr(types, "GenerateVideosConfig",
                        lambda **kw: {"video_cfg": kw}, raising=False)
    out = GoogleProvider("k").generate_video("적금 캠페인", aspect="9:16")
    assert out == b"REAL_VEO_VIDEO_BYTES"
    assert called.get("download") is True


def test_google_generate_video_prompt_has_cinematic_ad_direction(monkeypatch):
    """Veo 래퍼가 시네마틱 광고 지시를 포함하되 no-text 가드를 유지한다."""
    genai = pytest.importorskip("google.genai")
    from google.genai import types
    from app.providers.google_client import GoogleProvider
    captured: dict = {}
    monkeypatch.setattr(genai, "Client", _fake_genai_video(captured).Client)
    monkeypatch.setattr(types, "GenerateVideosConfig",
                        lambda **kw: {"video_cfg": kw}, raising=False)
    GoogleProvider("k").generate_video("적금 캠페인 키비주얼", aspect="9:16")
    p = captured["prompt"]
    assert "시네마틱" in p and "광고" in p   # 실광고 연출 지시
    assert "글자" in p                       # no-text 가드 유지(컴플라이언스)
    assert "적금 캠페인 키비주얼" in p        # 호출측 프롬프트 보존


def test_tracked_provider_delegates_generate_video():
    """TrackedProvider가 generate_video를 위임(미구현이면 V2a가 항상 still 폴백했던 버그)."""
    from app.providers.wrappers import TrackedProvider

    class _Inner:
        name = "demo"
        _model = "demo-1"
        def generate_video(self, prompt, *, aspect="9:16", duration_sec=15, fps=30):
            return b"\x00\x00\x00 ftypisom_VIDEO"

    tp = TrackedProvider(_Inner(), store=None, run_id="r", step="video", settings=None)
    out = tp.generate_video("배경", aspect="9:16", duration_sec=8)
    assert out == b"\x00\x00\x00 ftypisom_VIDEO"


def test_modelbound_provider_delegates_generate_video(monkeypatch):
    from app.providers import wrappers

    class _P:
        def generate_video(self, prompt, *, aspect="9:16", duration_sec=15, fps=30):
            return b"MB_VIDEO_BYTES"

    monkeypatch.setattr(wrappers, "get_provider", lambda name, settings: _P())
    monkeypatch.setattr(wrappers, "_model_map", lambda s: {})
    mb = wrappers.ModelBoundProvider("demo", None)
    assert mb.generate_video("배경", aspect="9:16") == b"MB_VIDEO_BYTES"
