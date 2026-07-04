"""업로드 이미지 하이라이트 — 데모 자산·mock bbox·seam·resolve 통합."""
import os
from PIL import Image

_POSTER = os.path.join(os.path.dirname(__file__), "..", "..",
                       "docs", "finals", "evidence", "upload-demo", "external-deposit-promo.png")


def test_demo_poster_exists_and_dims():
    assert os.path.exists(_POSTER), "make_poster.py를 먼저 실행해 PNG 생성"
    with Image.open(_POSTER) as im:
        assert im.size == (1080, 1350)


import json
from app.providers.demo import _upload_audit_findings
from app.providers.demo_fixtures import UPLOAD_HIGHLIGHT_BBOX


def test_mock_stub_attaches_bbox_for_designated_file():
    out = _upload_audit_findings("[uploaded-audit] file=external-deposit-promo.png\n...")
    f = json.loads(out)["findings"][0]
    assert f["location"]["bbox"] == UPLOAD_HIGHLIGHT_BBOX["external-deposit-promo.png"]
    assert f["location"]["slot"] == "uploaded"


def test_mock_stub_trigger_file_without_fixture_has_no_bbox():
    # 트리거는 맞지만(위반 포함) 지정 파일 아님 → finding 있으나 bbox 없음
    out = _upload_audit_findings("[uploaded-audit] file=랜덤_위반소재.png\n...")
    f = json.loads(out)["findings"][0]
    assert "bbox" not in f.get("location", {})


def test_mock_stub_non_trigger_non_fixture_empty():
    out = _upload_audit_findings("[uploaded-audit] file=평범한소재.png\n...")
    assert json.loads(out)["findings"] == []


from app.gateway.harness_review import _uploaded_location


def test_uploaded_location_preserves_bbox():
    f = {"location": {"slot": "uploaded", "lang": None, "bbox": {"x": 0.08, "y": 0.34, "w": 0.84, "h": 0.11}}}
    loc = _uploaded_location("external-deposit-promo.png", f)
    assert loc["slot"] == "uploaded:external-deposit-promo.png"
    assert loc["lang"] is None
    assert loc["bbox"] == {"x": 0.08, "y": 0.34, "w": 0.84, "h": 0.11}


def test_uploaded_location_no_bbox_when_absent():
    loc = _uploaded_location("x.png", {"location": {"slot": "uploaded", "lang": None}})
    assert loc == {"slot": "uploaded:x.png", "lang": None}
    assert "bbox" not in loc
