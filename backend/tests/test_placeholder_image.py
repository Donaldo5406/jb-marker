"""core/placeholder_image — 의존 없는 그라데이션 PNG 폴백(1×1 아님)."""
import struct

from app.core.placeholder_image import placeholder_png

_SIG = b"\x89PNG\r\n\x1a\n"


def _dims(png: bytes) -> tuple[int, int]:
    # IHDR data는 시그(8) + 길이(4) + "IHDR"(4) 다음 위치(16)에서 시작, width/height 각 4바이트.
    assert png[:8] == _SIG
    w, h = struct.unpack(">II", png[16:24])
    return w, h


def test_valid_png_signature_and_iend():
    png = placeholder_png("1:1")
    assert png[:8] == _SIG
    # 마지막 청크 = 길이(0) + "IEND" + crc → 끝 8바이트는 "IEND"+crc.
    assert png[-8:] == b"IEND" + struct.pack(">I", 0xAE426082)
    assert png[-12:-8] == struct.pack(">I", 0)  # IEND 데이터 길이 0


def test_square_dimensions():
    assert _dims(placeholder_png("1:1")) == (1024, 1024)


def test_portrait_4x5_dimensions():
    # 4:5 세로 포스터 — 빈 정사각 폴백 회귀 방지.
    assert _dims(placeholder_png("4:5")) == (1024, 1280)


def test_arbitrary_ratio_parsed():
    w, h = _dims(placeholder_png("2:1"))
    assert w == 1024 and h == 512


def test_unknown_aspect_falls_back_square():
    assert _dims(placeholder_png("garbage")) == (1024, 1024)


def test_extreme_ratio_clamps_to_min_1px():
    # 극단 비율에서도 0px(무효 PNG) 방지 — 최소 1px 보장.
    w, h = _dims(placeholder_png("1:5000"))
    assert w >= 1 and h >= 1


def test_not_one_pixel_blank():
    # 핵심 회귀: 폴백이 1×1 투명 PNG('아무것도 안 보임')가 아니어야 한다.
    png = placeholder_png("4:5")
    assert len(png) > 1000
    assert _dims(png) != (1, 1)
