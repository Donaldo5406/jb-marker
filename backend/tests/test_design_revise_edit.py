"""revise 재베이크 img2img(spec 2026-07-04) — 교정은 기존 v1.png 위 텍스트 교체(edit),
부재/실패 시 전체 재베이크 폴백. edit 프롬프트는 슬롯 색·크기 힌트를 보존(mock 골드 축 신호).
"""
import json

from app.gateway.harness import HarnessRequest
from app.gateway.harness_design import DesignHarness
from app.providers.base import ProviderResponse
from app.providers.fake import FakeProvider
from app.vfs.local import LocalVfsStore

SPEC = "/r1/design/rough/layout.spec.json"
V1 = "/r1/design/design-system/components/visual/v1.png"
PREV_PNG = b"\x89PNG\r\n\x1a\nPREV"


class _Recorder(FakeProvider):
    """generate_image 호출을 기록하는 이미지 프로바이더 — image kwarg 전달 검증용."""

    def __init__(self):
        super().__init__()
        self.calls = []

    def generate_image(self, prompt, *, aspect="1:1", image=None, image_size=None):
        self.calls.append({"prompt": prompt, "image": image, "aspect": aspect})
        return b"\x89PNG\r\n\x1a\nEDITED" + str(len(self.calls)).encode()

    def review_image(self, png, prompt, *, mime="image/png"):
        return ProviderResponse(text='{"findings": []}', model="fake")


def _store(tmp_path, *, with_visual: bool, languages=("ko", "en")):
    s = LocalVfsStore(storage_dir=str(tmp_path))
    s.create_run("r1", languages=list(languages))
    s.put("/r1/brainstorming/plan.md",
          "---\nfactsheet:\n  interest_rate: \"연 3.5%\"\nlanguages: [ko, en]\n---\n본문",
          source="marker", mime="text/markdown")
    s.put("/r1/design/_state.json", json.dumps(
        {"step": "done", "gate": None, "confirmed": {}, "bypass": {},
         "languages": list(languages), "pending_ask": None}),
        source="marker", mime="application/json")
    s.put(SPEC, json.dumps({
        "aspect": "4:5", "visual_concept": "골드 캘리 컨셉",
        "slots": [{"role": "headline", "copy_key": "headline", "color": "#FFD166",
                   "font_px": 88, "bbox": {"x": 0, "y": 0, "w": 900, "h": 200}}],
        "copy": {"ko": {"headline": "연 3.5% JB 정기예금", "body": "12개월", "cta": "가입"},
                 "en": {"headline": "JB Term Deposit at 3.5%", "body": "12-month",
                        "cta": "Open now"}}}, ensure_ascii=False),
        source="marker", mime="application/json")
    if with_visual:
        s.put(V1, PREV_PNG, source="gemini", mime="image/png")
    return s


def _remediate(store, image_provider, monkeypatch):
    monkeypatch.delenv("RICH_VECTOR_CHROME", raising=False)   # baked 경로
    monkeypatch.delenv("DIRECTED_FULLBAKE", raising=False)
    h = DesignHarness(image_provider=image_provider)
    req = HarnessRequest(run_id="r1", studio="design",
                         user_prompt="리뷰 결과대로 카피 교정해줘",
                         provider="fake", is_marker=True, action="")
    return h.handle_turn(req, provider=FakeProvider(), store=store)


def test_run_edit_uses_previous_visual_as_image_input(tmp_path, monkeypatch):
    s = _store(tmp_path, with_visual=True)
    rec = _Recorder()
    res = _remediate(s, rec, monkeypatch)
    assert res.meta.get("remediated") is True
    # 1콜 = 주 언어 편집: 기존 v1.png 바이트를 image 입력으로.
    assert rec.calls, "generate_image가 호출돼야 함"
    assert rec.calls[0]["image"] == PREV_PNG
    assert rec.calls[0]["prompt"].startswith("이 포스터의 텍스트만")
    # 슬롯 힌트 보존 — mock 골드 축(demo._headline_gold) 신호가 edit 프롬프트에도 실린다.
    assert "(색 #FFD166" in rec.calls[0]["prompt"]
    # 2콜 = 언어 변형: 새(편집된) v1을 베이스로 편집.
    new_v1 = s.get(V1).blob
    assert new_v1 == b"\x89PNG\r\n\x1a\nEDITED1"   # 1콜 결과가 v1.png로 저장됨
    assert rec.calls[1]["image"] == new_v1
    assert s.get("/r1/design/design-system/components/visual/v1.en.png") is not None


def test_run_edit_falls_back_to_full_bake_without_previous_visual(tmp_path, monkeypatch):
    s = _store(tmp_path, with_visual=False)
    rec = _Recorder()
    res = _remediate(s, rec, monkeypatch)
    assert res.meta.get("remediated") is True
    # 기존 비주얼 부재 → run()(전체 재베이크) 폴백: 첫 호출은 image 입력 없음.
    assert rec.calls and rec.calls[0]["image"] is None
    assert s.get(V1) is not None


def test_remediation_serves_v2_and_lang_fixtures(monkeypatch):
    """mock 통합 — 티키타카(골드) 완주 후 교정: v1=poster_v2, 언어 변형=poster_v2_{lang}.

    edit 프롬프트의 슬롯 힌트 + 언어 fixture 로더가 실제 remediate 경로에서 작동함을 확증."""
    from test_demo_pipeline import _client, _run, _seed_brainstorming

    from app.providers.demo_fixtures import load_poster_fixture
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]
    _seed_brainstorming(client, rid)
    _run(client, rid, "design", "디자인 시작", action="advance")          # S1 게이트
    _run(client, rid, "design", "헤드라인을 캘리그래피 골드로")            # 티키타카 → V2
    bm = {st: True for st in ("S1", "S2a", "S2b", "S2c", "S3")}
    _run(client, rid, "design", "계속", action="advance", bypass_map=bm)  # 완주
    r = _run(client, rid, "design", "리뷰 결과대로 카피 교정해줘")
    assert (r.json().get("meta") or {}).get("remediated") is True

    expected = load_poster_fixture("v2")
    if expected:
        png = client.get(f"/vfs/{rid}/design/design-system/components/visual/v1.png").content
        assert png == expected
    for lg in ("en", "vi", "zh"):
        exp = load_poster_fixture("v2", lg)
        if exp:
            var = client.get(
                f"/vfs/{rid}/design/design-system/components/visual/v1.{lg}.png").content
            assert var == exp, f"{lg} 변형이 poster_v2_{lg} fixture와 불일치"
