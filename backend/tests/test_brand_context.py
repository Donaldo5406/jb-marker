"""brand_context — JB 브랜드 지식 팩 로더·렌더 (spec 2026-07-04 D1·D2).

계약: 저변동 계층(identity·palette·tone_hints)만 렌더. products는 절대 렌더 금지
(수치·상품 상태 SSOT는 plan.md 팩트시트·Stage A 리서치). 부재·파싱 실패는 None 강하."""
import os

from app.gateway.design.brand_context import load_brand_pack, render_brand_block


def test_load_brand_pack_returns_dict_with_required_sections():
    pack = load_brand_pack()          # 기본 jb_group
    assert isinstance(pack, dict)
    assert pack["meta"]["brand_id"] == "jb_group"
    assert "identity" in pack and "palette" in pack


def test_load_missing_pack_returns_none():
    assert load_brand_pack("no_such_brand") is None


def test_render_includes_priority_clause_and_palette():
    block = render_brand_block(load_brand_pack())
    assert block.startswith("[brand_context")
    assert "우선" in block                      # 사용자 지시·토큰 우선 명시
    assert "#051D49" in block                   # 워드마크 네이비(실측)
    assert "#0098D7" in block                   # 심볼 블루 첫 단계
    assert "따뜻한 금융" in block                # 슬로건
    assert block.count("\n") <= 7               # 4~6줄 컴팩트 렌더(헤더 포함 ≤8줄)


def test_render_never_leaks_products():
    """고변동 정보(상품·금리) 주입 금지 — 시의성 오류의 구조적 차단."""
    pack = load_brand_pack()
    assert pack.get("products")                 # 팩에는 존재하지만
    block = render_brand_block(pack)
    assert "청년도약" not in block               # 렌더에는 절대 없음
    assert "주거래 플러스" not in block
    assert "%" not in block                     # 금리류 수치 없음


def test_render_partial_pack_renders_available_sections():
    block = render_brand_block({"tone_hints": {"keywords": ["신뢰", "따뜻함"]}})
    assert "신뢰" in block and "[brand_context" in block


def test_render_none_or_empty_returns_none():
    assert render_brand_block(None) is None
    assert render_brand_block({}) is None


def test_s1_system_prompt_includes_brand_block(tmp_path):
    """S1Rough가 브랜드 블록을 레퍼런스 말미에 포함해 조립하는지 — 기존 순서(D6) 불변."""
    import json
    from app.gateway.design.steps import S1Rough
    from app.gateway.harness import HarnessRequest
    from app.gateway.pipeline import StepContext
    from app.providers.fake import FakeProvider
    from app.vfs.local import LocalVfsStore

    class _CapturingProvider(FakeProvider):
        def __init__(self):
            self.systems = []

        def complete(self, messages, *, model=None, system=None, tools=None, **kw):
            self.systems.append(system or "")
            return super().complete(messages, model=model, system=system,
                                    tools=tools, **kw)

    store = LocalVfsStore(storage_dir=str(tmp_path))
    store.create_run("r1", languages=["ko"])
    store.put("/r1/design/design-system/tokens.json",
              json.dumps({"palette": []}), source="marker", mime="application/json")
    provider = _CapturingProvider()
    req = HarnessRequest(run_id="r1", studio="design", user_prompt="",
                         provider="fake", is_marker=True, action="advance")
    ctx = StepContext(req=req, provider=provider, store=store,
                      state={"step": "S1", "gate": None, "confirmed": {},
                             "bypass": {}, "languages": ["ko"]},
                      base="/r1/design")
    S1Rough().run(ctx)
    sys_prompt = provider.systems[0]
    assert "[brand_context" in sys_prompt
    assert "우선" in sys_prompt                       # 사용자 우선 문구 도달 확인
    # 기존 조립 순서 불변: tokens → references → brand_context
    assert sys_prompt.index("[tokens]") < sys_prompt.index("[references]") \
        < sys_prompt.index("[brand_context")
