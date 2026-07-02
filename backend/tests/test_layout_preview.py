"""design/layout_preview.py — 결정론 self-contained HTML 시안 렌더러 (spec 2026-07-03 §1·§5)."""
import random
from io import BytesIO

from PIL import Image

from app.gateway.design.layout_preview import build_layout_mock_html


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
    # _downscale_inline이 그라데이션 PNG를 더 작은 JPEG로 변환 → 경유 확인.
    assert "data:image/jpeg;base64," in out


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
