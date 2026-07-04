"""design/layout_preview.py — 결정론 self-contained HTML 시안 렌더러 (spec 2026-07-03 §1·§5)."""
import random
from html.parser import HTMLParser
from io import BytesIO

from PIL import Image

from app.gateway.design.layout_preview import build_layout_mock_html


class _AttrCollector(HTMLParser):
    """브라우저 동일 알고리즘(html.parser)으로 태그 속성을 실제 파싱해 수집."""

    def __init__(self):
        super().__init__()
        self.divs: list[dict] = []

    def handle_starttag(self, tag, attrs):
        if tag == "div":
            self.divs.append(dict(attrs))


def _canvas_style(out: str) -> str:
    """파싱된 canvas div의 style 속성값(따옴표 충돌 시 조기 종료된 값이 그대로 드러남)."""
    p = _AttrCollector()
    p.feed(out)
    canvases = [d for d in p.divs if d.get("class") == "canvas"]
    assert len(canvases) == 1
    return canvases[0].get("style") or ""


def _png_bytes(w: int = 720, h: int = 540) -> bytes:
    """Pillow로 즉석 생성한 시드 노이즈 PNG(1x1 아님, >640px). 노이즈는 PNG 압축이 나빠
    _downscale_inline이 더 작은 JPEG로 변환(+썸네일 다운스케일) → 경유 확인용."""
    rnd = random.Random(1234)
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = (rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255))
    buf = BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _spec() -> dict:
    return {
        "aspect": "4:5",
        "bg_color": "#F2EFE9",
        "visual_concept": "밝은 채광의 카페 창가, 20대 청년이 통장을 들고 미소",
        "slots": [
            {"role": "headline", "bbox": {"x": 80, "y": 120, "w": 920, "h": 180},
             "z": 3, "copy_key": "headline", "font_px": 96, "color": "#0B1324"},
            {"role": "body", "bbox": {"x": 80, "y": 340, "w": 900, "h": 120},
             "z": 2, "copy_key": "body", "font_px": 40, "color": "#1A2332"},
            {"role": "cta", "bbox": {"x": 80, "y": 980, "w": 520, "h": 96},
             "z": 3, "copy_key": "cta", "font_px": 44, "color": "#FFFFFF"},
        ],
        "copy": {"ko": {"headline": "청년 적금으로 미래를 더 크게",
                        "body": "매달 자동이체로 목돈 만들기",
                        "cta": "지금 신청"}},
    }


def _tokens() -> dict:
    return {"palette": ["#0B1324", "#F2C94C"], "color_palette": ["#1A2332"],
            "font": "Pretendard", "grid": "12col", "aspect": "4:5"}


def _facts() -> dict:
    return {"상품명": "청년 적금", "기본금리": "3.5%", "최고금리": "5.0%"}


def test_deterministic_same_input_same_output():
    a = build_layout_mock_html(_spec(), _tokens(), _facts())
    b = build_layout_mock_html(_spec(), _tokens(), _facts())
    assert a == b
    assert a.startswith("<!doctype html>")


def test_escapes_malicious_copy():
    spec = _spec()
    spec["copy"]["ko"]["headline"] = "<script>alert(1)</script>"
    out = build_layout_mock_html(spec, _tokens(), _facts())
    assert "<script" not in out
    assert "&lt;script&gt;" in out


def test_escapes_malicious_visual_concept():
    spec = _spec()
    spec["visual_concept"] = "<img src=x onerror=alert(1)>"
    out = build_layout_mock_html(spec, _tokens(), _facts())
    assert "<img src=x" not in out
    assert "&lt;img" in out


def test_visual_none_has_no_data_uri():
    out = build_layout_mock_html(_spec(), _tokens(), _facts(), visual_png=None)
    assert "data:image" not in out


def test_visual_png_inlined_via_downscale():
    out = build_layout_mock_html(_spec(), _tokens(), _facts(), visual_png=_png_bytes())
    assert "data:image" in out
    # _downscale_inline이 노이즈 PNG를 더 작은 JPEG로 변환 → 경유 확인.
    assert "data:image/jpeg;base64," in out
    # 문자열 존재만으로는 부족(과거 버그: url('data:...')의 작은따옴표가 바깥 style='...'
    # 속성을 조기 종료 → 브라우저에서 배경 미렌더). html.parser로 실제 파싱해 style
    # 속성값 **안에** background-image url이 온전히 남아 있는지 단언한다.
    style = _canvas_style(out)
    assert 'background-image:url("data:image/jpeg;base64,' in style
    assert style.rstrip().endswith('")')


def test_self_contained_no_external_urls():
    out = build_layout_mock_html(_spec(), _tokens(), _facts(), visual_png=_png_bytes())
    assert "http://" not in out
    assert "https://" not in out


def test_empty_inputs_no_crash():
    out = build_layout_mock_html({}, {}, {})
    assert out.startswith("<!doctype html>")
    assert "</html>" in out
    assert "data:image" not in out


def test_malformed_slots_are_skipped():
    spec = {
        "aspect": "1:1",
        "slots": [
            "not-a-dict",
            {"role": "headline"},                       # bbox 없음 → skip
            {"role": "cta", "bbox": "bad"},             # bbox가 dict 아님 → skip
            {"role": "body", "bbox": {"x": 10, "y": 20, "w": 100, "h": 50},
             "copy_key": "body"},                       # 유효
        ],
        "copy": {"ko": {"body": "유효 슬롯"}},
    }
    out = build_layout_mock_html(spec, {}, {})
    assert out.startswith("<!doctype html>")
    # 유효 슬롯 1개만 렌더(role 라벨 '바디' 1회).
    assert out.count("class='slot'") == 1
    assert "유효 슬롯" in out


def test_none_arguments_do_not_crash():
    out = build_layout_mock_html(None, None, None)
    assert out.startswith("<!doctype html>")


def test_visual_png_hides_baked_text_slots_keeps_overlays():
    """베이크 후 프리뷰는 오버레이 슬롯(logo·disclosure)만 — headline/body/cta 박스를
    다시 얹으면 풀베이크의 실제 배치와 어긋난 이중 텍스트가 된다(실측 2026-07-03)."""
    spec = dict(_spec())
    spec["slots"] = list(spec["slots"]) + [
        {"role": "logo", "bbox": {"x": 80, "y": 48, "w": 160, "h": 56}, "z": 3},
        {"role": "disclosure", "bbox": {"x": 80, "y": 1276, "w": 920, "h": 58},
         "z": 3, "copy_key": "disclosure", "font_px": 26, "color": "#3A3A3A"},
    ]
    out = build_layout_mock_html(spec, _tokens(), _facts(), visual_png=_png_bytes())
    # 베이크된 텍스트 카피 미방출(포스터에 이미 구워짐 — 이중 텍스트 방지)
    assert "청년 적금으로 미래를 더 크게" not in out
    assert "매달 자동이체로 목돈 만들기" not in out
    # 오버레이 슬롯은 유지(로고·고지 자리 표시)
    assert "로고" in out and "고지" in out
    # visual 없으면 현행 그대로(텍스트 박스 렌더)
    out_pre = build_layout_mock_html(spec, _tokens(), _facts(), visual_png=None)
    assert "헤드라인" in out_pre


def test_vector_chrome_keeps_text_slots_with_visual():
    """vector_chrome은 텍스트가 벡터 오버레이(미베이크) — visual이 있어도 전 슬롯 유지."""
    spec = dict(_spec())
    spec["render_mode"] = "vector_chrome"
    out = build_layout_mock_html(spec, _tokens(), _facts(), visual_png=_png_bytes())
    assert "헤드라인" in out
