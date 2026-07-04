"""업로드 이미지 하이라이트 — 데모 자산·mock bbox·seam·resolve 통합."""
import os
from PIL import Image

_POSTER = os.path.join(os.path.dirname(__file__), "..", "..",
                       "docs", "finals", "evidence", "upload-demo", "external-deposit-promo.png")


def test_demo_poster_exists_and_dims():
    assert os.path.exists(_POSTER), "make_poster.py를 먼저 실행해 PNG 생성"
    with Image.open(_POSTER) as im:
        assert im.size == (1080, 1350)
