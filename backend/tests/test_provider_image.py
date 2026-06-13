"""Provider.generate_image 계약 테스트 (이미지 액터 — marker_api.md M4)."""
import pytest

from app.providers.base import Provider
from app.providers.fake import FakeProvider


def _fake_genai_module(captured: dict):
    """genai.Client(...).models.generate_content를 가로채 config를 기록하고
    이미지 파트를 가진 가짜 응답을 반환하는 fake genai 모듈 객체."""
    class _Inline:
        data = b"\x89PNG\r\n\x1a\n_img"

    class _Part:
        inline_data = _Inline()

    class _Content:
        parts = [_Part()]

    class _Cand:
        content = _Content()

    class _Resp:
        candidates = [_Cand()]

    class _Models:
        def generate_content(self, *, model, contents, config=None):
            captured["model"] = model
            captured["config"] = config
            return _Resp()

    class _Client:
        def __init__(self, *a, **k):
            self.models = _Models()

    import types as _t
    mod = _t.SimpleNamespace(Client=_Client)
    return mod


def test_base_generate_image_not_implemented():
    class Bare(Provider):
        def complete(self, messages, *, model, system=None, tools=None, **kw): ...

    import pytest
    with pytest.raises(NotImplementedError):
        Bare().generate_image("배경", aspect="1:1")


def test_fake_generate_image_returns_png_bytes():
    out = FakeProvider().generate_image("연한 블루 그라디언트 배경", aspect="1:1")
    assert isinstance(out, bytes)
    assert out[:8] == b"\x89PNG\r\n\x1a\n"   # PNG 시그니처


def test_google_generate_image_passes_aspect_ratio(monkeypatch):
    """FIX: 종횡비를 image_config.aspect_ratio로 전달해야 실제 적용된다(프롬프트 텍스트는 무시됨)."""
    genai = pytest.importorskip("google.genai")  # live extra 미설치 시 skip
    from app.providers.google_client import GoogleProvider

    captured: dict = {}
    monkeypatch.setattr(genai, "Client", _fake_genai_module(captured).Client)
    # 모델명은 이 테스트 관심사 아님(aspect 전달 검증) — 기본값 변경과 분리되게 명시 주입.
    out = GoogleProvider("k", image_model="gemini-2.5-flash-image").generate_image(
        "프리미엄 금융 배경", aspect="4:5")

    assert out[:8] == b"\x89PNG\r\n\x1a\n"
    assert captured["model"] == "gemini-2.5-flash-image"
    cfg = captured["config"]
    assert cfg is not None and cfg.image_config.aspect_ratio == "4:5"


def test_google_generate_image_omits_config_for_unsupported_aspect(monkeypatch):
    """미지원 종횡비는 image_config 생략(모델 에러 회피 → 폴백은 호출측 책임)."""
    genai = pytest.importorskip("google.genai")
    from app.providers.google_client import GoogleProvider

    captured: dict = {}
    monkeypatch.setattr(genai, "Client", _fake_genai_module(captured).Client)
    GoogleProvider("k").generate_image("배경", aspect="7:13")
    assert captured["config"] is None


def test_google_generate_image_passes_input_image_as_part(monkeypatch):
    """image 주어지면 contents 앞에 Part.from_bytes(편집 모드)로 넣는다."""
    import sys, types as _t
    captured = {}
    genai = _t.ModuleType("google.genai"); google = _t.ModuleType("google")
    types_mod = _t.ModuleType("google.genai.types")
    class _Part:
        @staticmethod
        def from_bytes(*, data, mime_type): return ("PART", data, mime_type)
    class _ImageConfig:
        def __init__(self, **k): self.k = k
    class _Cfg:
        def __init__(self, **k): self.k = k
    types_mod.Part = _Part; types_mod.ImageConfig = _ImageConfig
    types_mod.GenerateContentConfig = _Cfg
    class _Resp:
        class _C:
            class _Content:
                parts = [_t.SimpleNamespace(inline_data=_t.SimpleNamespace(data=b"OUT"))]
            content = _Content()
        candidates = [_C()]
    class _Client:
        def __init__(self, **k): self.models = self
        def generate_content(self, *, model, contents, config=None):
            captured["contents"] = contents; return _Resp()
    genai.Client = _Client; google.genai = genai
    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setitem(sys.modules, "google.genai", genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", types_mod)

    from app.providers.google_client import GoogleProvider
    out = GoogleProvider(api_key="x").generate_image("프롬프트", aspect="4:5", image=b"BASE")
    assert out == b"OUT"
    assert captured["contents"][0][0] == "PART"          # 첫 요소 = 입력 이미지 Part
    assert captured["contents"][0][1] == b"BASE"


def test_default_image_model_is_gemini_3_pro():
    """기본 이미지 모델=gemini-3-pro-image(한글 베이크 정확 — 2.5-flash 한글 깨짐 실측 회귀)."""
    from app.providers.google_client import GoogleProvider
    from app.observability import pricing
    assert GoogleProvider(api_key=None)._image_model == "gemini-3-pro-image"
    assert pricing.is_known("gemini-3-pro-image")
    assert pricing.image_cost_usd("gemini-3-pro-image", 1) > 0
