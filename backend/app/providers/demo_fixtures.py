"""시연용 Mock 파이프라인 고정 산출물 — 정기예금 캠페인 1세트(4언어).

각 단계 하네스가 기대하는 정확한 스키마를 만족해 BrainStorming→Deploy 전 구간을
결정적으로 완주시킨다. 수치는 factsheet와 일치해 grounding을 통과한다.
"""
from __future__ import annotations

import struct
import zlib

LANGUAGES = ["ko", "en", "vi", "zh"]

# 수치는 모든 copy와 일치해야 grounding 통과(3.5 / 12 / 100).
FACTSHEET = {
    "product": "JB 정기예금",
    "interest_rate": "3.5%",
    "term": "12개월",
    "min_amount": "100만원",
}

SPEC_MD = """---
goal: 2030 직장인 정기예금 신규 가입 유치
target_segments: [2030 직장인, 사회초년생]
key_messages: [높은 금리, 간편 가입]
channels: [email, kakao, instagram]
languages: [ko, en, vi, zh]
multinational: true
tone: 신뢰감 있고 친근한
factsheet:
  product: JB 정기예금
  interest_rate: 3.5%
  term: 12개월
  min_amount: 100만원
disclosures: [예금자보호법에 따라 5천만원까지 보호]
---
# 정기예금 신규 가입 캠페인 스펙

2030 직장인을 대상으로 연 3.5% 정기예금 신규 가입을 유치한다.
"""

PLAN_MD = """---
creative_direction:
  palette: ["#00857C", "#0B2B5B", "#FFFFFF"]
  font: Pretendard
  grid: 12col
  aspect: "1:1"
material_matrix: [{channel: instagram, format: square}, {channel: email, format: banner}]
image_concept: 밝은 톤의 추상적 금융 성장 이미지
copy_themes: [높은 금리, 간편 가입, 신뢰]
multinational: true
languages: [ko, en, vi, zh]
slots: [background, headline, body, cta]
factsheet:
  product: JB 정기예금
  interest_rate: 3.5%
  term: 12개월
  min_amount: 100만원
disclosures: [예금자보호법에 따라 5천만원까지 보호]
---
# 구현 계획

레이아웃·카피·비주얼을 4개 언어로 산출한다.
"""

LAYOUT_SPEC = {
    "visual_concept": "밝은 톤의 추상적 금융 성장 이미지",
    "aspect": "1:1",
    # bbox는 레퍼런스·실 LLM·프론트 assembleScene과 동일한 {x,y,w,h} 객체 형식.
    # (이전 배열 [x1,y1,x2,y2] 코너 형식은 프론트가 s.bbox.x로 읽어 좌표가 전부
    #  undefined가 되는 버그를 유발 → 텍스트가 원점에 겹치고 배경이 안 채워졌다.)
    "slots": [
        {"role": "background", "bbox": {"x": 0, "y": 0, "w": 1080, "h": 1080}, "z": 0, "copy_key": None},
        {"role": "headline", "bbox": {"x": 80, "y": 120, "w": 840, "h": 180}, "z": 1, "copy_key": "headline"},
        {"role": "body", "bbox": {"x": 80, "y": 340, "w": 840, "h": 260}, "z": 1, "copy_key": "body"},
        {"role": "cta", "bbox": {"x": 80, "y": 900, "w": 440, "h": 100}, "z": 2, "copy_key": "cta"},
    ],
    "copy": {},
}

# 모든 수치(3.5 / 12 / 100)는 FACTSHEET에 존재 → grounding 통과.
COPY = {
    "ko": {"headline": "연 3.5% JB 정기예금", "body": "12개월 만기, 100만원부터 시작하세요.", "cta": "지금 가입하기"},
    "en": {"headline": "JB Deposit at 3.5%", "body": "12-month term, from 100만원.", "cta": "Open now"},
    "vi": {"headline": "JB tiết kiệm 3.5%", "body": "Kỳ hạn 12개월, từ 100만원.", "cta": "Mở ngay"},
    "zh": {"headline": "JB定期存款 3.5%", "body": "12개월 期限, 100만원 起.", "cta": "立即开户"},
}

CRITIC_SCORES = {
    "hierarchy": 4, "grid": 4, "whitespace": 4, "cta": 4,
    "compliance": 5, "copy_visual": 4, "brand": 4,
}


def _png_chunk(typ: bytes, data: bytes) -> bytes:
    body = typ + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def placeholder_png(width: int = 512, height: int = 512, rgb: tuple = (0, 133, 124)) -> bytes:
    """의존 없이 단색(JB 그린) PNG 생성 — 시연 비주얼 placeholder(1x1 더미 대체)."""
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    row = b"\x00" + bytes(rgb) * width
    raw = row * height
    idat = zlib.compress(raw, 9)
    return sig + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", idat) + _png_chunk(b"IEND", b"")
