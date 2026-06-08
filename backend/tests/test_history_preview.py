"""History preview — design-system → self-contained HTML 빌더."""
import json

from app.history.preview import build_preview_html
from app.vfs.local import LocalVfsStore


def _seed_design(store, run_id="r1", *, with_visual=True):
    store.create_run(run_id, user_id="u1", languages=["ko"])
    tokens = {"palette": ["#0b1324", "#f5a623"], "font": "Inter",
              "grid": "12col", "aspect": "1:1"}
    store.put(f"/{run_id}/design/design-system/tokens.json",
              json.dumps(tokens), mime="application/json", source="marker")
    store.put(f"/{run_id}/design/design-system/components/headline/ko.txt",
              "큰 혜택", mime="text/plain", source="marker")
    if with_visual:
        store.put(f"/{run_id}/design/design-system/components/visual/v1.png",
                  b"\x89PNG\r\n\x1a\nFAKE", mime="image/png", source="gemini")


def test_preview_contains_palette_and_font():
    s = LocalVfsStore()
    _seed_design(s)
    html = build_preview_html("r1", s)
    assert "#0b1324" in html
    assert "Inter" in html
    assert "큰 혜택" in html
    # 회귀 가드: 가짜 마케팅 카피를 타이포 샘플로 발명하지 않는다.
    assert "금융 마케팅을 쉽게" not in html


def test_preview_inlines_visual_as_base64_data_uri():
    s = LocalVfsStore()
    _seed_design(s, with_visual=True)
    html = build_preview_html("r1", s)
    assert "data:image/png;base64," in html


def test_preview_downscales_large_visual():
    """풀해상도 비주얼은 썸네일로 다운스케일돼 인라인된다(프리뷰 ~10초 지연 회귀 가드)."""
    import base64 as _b64
    import re
    from io import BytesIO

    Image = __import__("pytest").importorskip("PIL.Image", reason="Pillow 미설치")
    s = LocalVfsStore()
    _seed_design(s, with_visual=False)
    big = Image.new("RGB", (1600, 1600), (11, 19, 36))
    buf = BytesIO()
    big.save(buf, format="PNG")
    raw = buf.getvalue()
    s.put("/r1/design/design-system/components/visual/v1.png",
          raw, mime="image/png", source="gemini")

    html = build_preview_html("r1", s)
    m = re.search(r"data:image/\w+;base64,([A-Za-z0-9+/=]+)", html)
    assert m, "비주얼 data URI 인라인 유지"
    inlined = _b64.b64decode(m.group(1))
    assert len(inlined) < len(raw)          # 줄어듦
    assert len(inlined) < 120_000           # 충분히 경량(원본 대비 수십분의 1)


def test_preview_visual_graceful_when_undecodable():
    """디코드 불가 바이트는 원본 mime(png)으로 graceful 인라인 — 크래시 없음."""
    s = LocalVfsStore()
    _seed_design(s, with_visual=True)  # b"\x89PNG...FAKE" = 디코드 불가
    html = build_preview_html("r1", s)
    assert "data:image/png;base64," in html


def test_preview_self_contained_no_external_src():
    s = LocalVfsStore()
    _seed_design(s)
    html = build_preview_html("r1", s)
    # 외부 네트워크 의존 금지: http(s) 절대 URL src 없음
    assert 'src="http' not in html


def test_preview_sanitizes_descriptive_font_in_css():
    """서술형 typography가 tokens.font로 새도 CSS font-family를 깨지 않고, 서술은 노트로 보존."""
    s = LocalVfsStore()
    s.create_run("r3", user_id="u1", languages=["ko"])
    desc = "헤드라인은 굵고 크게(숫자 강조), 본문은 가독성 높은 산세리프"
    tokens = {"palette": ["#0b1324"], "font": desc, "grid": "12col", "aspect": "1:1"}
    s.put("/r3/design/design-system/tokens.json",
          json.dumps(tokens, ensure_ascii=False), mime="application/json", source="marker")
    html = build_preview_html("r3", s)
    style_block = html.split("</style>")[0]
    assert "(숫자 강조)" not in style_block        # 서술 문장이 CSS에 새지 않음
    assert "font-family:헤드라인" not in html       # font-family는 안전한 폰트명만
    assert "font-family:Inter" in html              # 안전 폴백
    assert desc in html                             # 서술 정보는 타이포 노트로 보존


def test_preview_empty_when_no_design_system():
    s = LocalVfsStore()
    s.create_run("r2", user_id="u1")
    html = build_preview_html("r2", s)
    assert "<html" in html.lower()
    assert "디자인" in html  # 안내 문구


# --- 라우트 통합 ---
from fastapi.testclient import TestClient
from app.server import create_app


def test_preview_route_returns_html():
    c = TestClient(create_app())
    run_id = c.post("/runs", json={"title": "n"}).json()["run_id"]
    c.put(f"/vfs/{run_id}/design/design-system/tokens.json",
          json={"content": json.dumps({"palette": ["#abcdef"], "font": "Inter"}),
                "mime": "application/json"})
    r = c.get(f"/runs/{run_id}/preview")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "#abcdef" in r.text


def test_preview_route_empty_when_no_design():
    c = TestClient(create_app())
    run_id = c.post("/runs", json={"title": "n"}).json()["run_id"]
    r = c.get(f"/runs/{run_id}/preview")
    assert r.status_code == 200
    assert "디자인" in r.text


def test_preview_route_404_for_missing_run():
    c = TestClient(create_app())
    assert c.get("/runs/nope/preview").status_code == 404
