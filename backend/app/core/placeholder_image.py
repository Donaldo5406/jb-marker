"""의존 없는 PNG placeholder — 실 이미지 생성 불가(GOOGLE_API_KEY 부재 등) 시 보이는 대체 비주얼.

기존 fake 폴백은 1×1 투명 PNG라 캔버스에 '아무것도 안 나오는' 것처럼 보였다. 이 모듈은
종횡비에 맞는 세로 그라데이션(JB 네이비→그린) PNG를 stdlib(zlib+struct)로 직접 인코딩해
키 없이도 '키비주얼처럼 보이는' 대체 배경을 제공한다(시연·실모드 폴백 공용).
"""
from __future__ import annotations

import struct
import zlib

# 종횡비 → (width, height) 매핑(긴 변 ~1024px). 미지정/이상값은 1:1로 폴백.
_ASPECTS = {
    "1:1": (1024, 1024), "4:5": (1024, 1280), "5:4": (1280, 1024),
    "16:9": (1280, 720), "9:16": (720, 1280), "3:4": (960, 1280), "4:3": (1280, 960),
}

# 기본 그라데이션(JB 네이비 → JB 그린).
_TOP = (11, 43, 91)
_BOTTOM = (0, 133, 124)


def _dims(aspect: str | None) -> tuple[int, int]:
    if aspect in _ASPECTS:
        return _ASPECTS[aspect]
    try:
        ws, hs = str(aspect).split(":")
        w, h = float(ws), float(hs)
        if w <= 0 or h <= 0:
            return _ASPECTS["1:1"]
        base = 1024
        dim = (base, int(round(base * h / w))) if w >= h else (int(round(base * w / h)), base)
        return (max(1, dim[0]), max(1, dim[1]))   # 극단 비율(예: 1:5000)에서 0px 무효 PNG 방지
    except Exception:
        return _ASPECTS["1:1"]


def _chunk(typ: bytes, data: bytes) -> bytes:
    body = typ + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def placeholder_png(aspect: str = "1:1", *,
                    top: tuple = _TOP, bottom: tuple = _BOTTOM) -> bytes:
    """종횡비에 맞는 세로 그라데이션 PNG 바이트(8-bit RGB). 의존 없음·결정론."""
    w, h = _dims(aspect)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit truecolor RGB
    rows = bytearray()
    denom = (h - 1) or 1
    for y in range(h):
        t = y / denom
        r = int(round(top[0] + (bottom[0] - top[0]) * t))
        g = int(round(top[1] + (bottom[1] - top[1]) * t))
        b = int(round(top[2] + (bottom[2] - top[2]) * t))
        rows.append(0)                       # 각 스캔라인 filter 바이트(None)
        rows += bytes((r, g, b)) * w
    idat = zlib.compress(bytes(rows), 9)
    return sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")
