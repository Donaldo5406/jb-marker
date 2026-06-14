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


def test_demo_generate_video_returns_bytes():
    out = DemoProvider().generate_video("추상 금융 배경", aspect="9:16")
    assert isinstance(out, bytes) and len(out) > 0


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
    assert captured["config"] == {"video_cfg": {"aspect_ratio": "9:16"}}
    assert "글자" in captured["prompt"]   # no-text 지시 포함


def test_google_generate_video_omits_config_for_unsupported_aspect(monkeypatch):
    genai = pytest.importorskip("google.genai")
    from app.providers.google_client import GoogleProvider
    captured: dict = {}
    monkeypatch.setattr(genai, "Client", _fake_genai_video(captured).Client)
    GoogleProvider("k").generate_video("배경", aspect="7:13")
    assert captured["config"] is None


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
