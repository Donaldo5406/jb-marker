"""Provider.complete meta 인자 수용 + model 완화 (spec §5.2·§5.3)."""
import inspect
import json

from app.providers.base import Message, Provider
from app.providers.fake import FakeProvider


def test_fake_accepts_meta_and_optional_model():
    r = FakeProvider().complete([Message("user", "hi")],
                                meta={"studio": "x", "step": "y"})
    assert r.text  # 수용만 — 무시


def test_demo_accepts_meta_keyword():
    from app.providers.demo import DemoProvider
    r = DemoProvider().complete([Message("user", "hi")], system=None,
                                meta={"studio": "brainstorming", "step": "stage_a"})
    assert r.text is not None


def _demo(meta, msgs=None, system=None):
    from app.providers.demo import DemoProvider
    return DemoProvider().complete(msgs or [Message("user", "x")],
                                   system=system, meta=meta)


def test_demo_routes_by_meta_table():
    """T7: meta{studio,step}만으로 9개 단계 전부 라우팅 — system 마커 불필요 증명 (spec §5.2).

    단언 표면은 test_demo_provider.py의 해당 시나리오와 동일. stage_b 서브상태 2케이스만
    system을 전달하는데, 이는 '[현재 plan.md]' 컨텍스트 블록의 **데이터 읽기**(단계 감지 아님)
    — 단계 마커는 어디에도 없다. 나머지는 system=None으로 meta 단독 라우팅을 증명.
    """
    # brainstorming/stage_a — 1턴: spec 미작성·질문(a)·리서치 인용 동반
    resp = _demo({"studio": "brainstorming", "step": "stage_a"})
    r = json.loads(resp.text)
    assert r["ready"] is False and r["document"] == ""
    assert r["ask"]["trigger"] == "a"
    assert len(resp.citations) >= 1
    assert resp.citations[0]["url"].startswith("http")

    # brainstorming/stage_b 서브상태①: 현재 plan 비어있음 → 누락 초안(ready=false)
    r = json.loads(_demo({"studio": "brainstorming", "step": "stage_b"},
                         system="페르소나\n\n[현재 plan.md]\n").text)
    assert r["ready"] is False
    assert "disclosures:" not in r["document"] and "slots:" not in r["document"]
    assert "creative_direction:" in r["document"]

    # brainstorming/stage_b 서브상태②: 현재 plan 존재 → 완성 plan(ready)
    r = json.loads(_demo(
        {"studio": "brainstorming", "step": "stage_b"},
        system="페르소나\n\n[현재 plan.md]\n---\ncreative_direction: x\n---\n초안").text)
    assert r["ready"] is True
    assert "disclosures:" in r["document"] and "slots:" in r["document"]

    # design/S1 — layout_spec
    r = json.loads(_demo({"studio": "design", "step": "S1"}).text)
    assert "slots" in r["layout_spec"]

    # design/S2b — 4언어 카피
    r = json.loads(_demo({"studio": "design", "step": "S2b"}).text)
    assert set(r["copy"]) == {"ko", "en", "vi", "zh"}

    # design/critic — scores
    r = json.loads(_demo({"studio": "design", "step": "critic"}).text)
    assert set(r["scores"]) >= {"hierarchy", "brand"}

    # review/R1 — 콘텐츠 기반 위반 적발(scene_copy는 user payload)
    violating = {"ko": {"headline": "업계 최고 연 4.0% 적금",
                        "body": "연 4.0%! 지금 가입하세요", "cta": "가입"}}
    r = json.loads(_demo(
        {"studio": "review", "step": "R1"},
        msgs=[Message("user", json.dumps({"scene_copy": violating},
                                         ensure_ascii=False))]).text)
    assert r["findings"]

    # review/R2 — 빈 findings(안전망 위임)
    r = json.loads(_demo({"studio": "review", "step": "R2"}).text)
    assert r["findings"] == []

    # review/R3 — verdicts 통합(reconcile)
    r = json.loads(_demo({"studio": "review", "step": "R3"},
                         msgs=[Message("user", json.dumps({"verdicts": []}))]).text)
    assert "recommendations" in r

    # meta 부재 / 미지 step(compact) → 안전 기본(빈 reply) — Passthrough 경로 보존
    assert json.loads(_demo(None).text) == {"reply": "", "ready": False}
    assert json.loads(_demo({"studio": "brainstorming", "step": "compact"}).text) \
        == {"reply": "", "ready": False}


def test_all_providers_declare_meta_and_optional_model():
    """5개 구현체 + ABC가 meta 명시 인자와 model 기본값 None을 선언."""
    from app.providers.anthropic_client import AnthropicProvider
    from app.providers.demo import DemoProvider
    from app.providers.fake import FakeProvider
    from app.providers.google_client import GoogleProvider
    from app.providers.openai_client import OpenAIProvider
    for cls in (Provider, AnthropicProvider, OpenAIProvider, GoogleProvider,
                FakeProvider, DemoProvider):
        sig = inspect.signature(cls.complete)
        assert "meta" in sig.parameters, cls.__name__
        assert sig.parameters["meta"].default is None, cls.__name__
        assert sig.parameters["model"].default is None, cls.__name__
