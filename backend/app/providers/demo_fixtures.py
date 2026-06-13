"""시연용 Mock 파이프라인 고정 산출물 — 정기예금 캠페인 1세트(4언어).

각 단계 하네스가 기대하는 정확한 스키마를 만족해 BrainStorming→Deploy 전 구간을
결정적으로 완주시킨다. 수치는 factsheet와 일치해 grounding을 통과한다.
"""
from __future__ import annotations

import os
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
  aspect: "4:5"
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
    # 4:5 세로형(인스타/카톡 피드 최적) — 사용자 제공 배경(1122×1402=4:5)을 꽉 채운다.
    # 프론트 assembleScene이 aspect로 캔버스 1080×1350을 산출 → 배경 클리핑 없음.
    "aspect": "4:5",
    # 시각 적법성 룰(core/visual_rules) 입력 — 배경 대표 톤(밝은 포스터). 고지 대비 계산 근거.
    "bg_color": "#F2EFE9",
    # bbox는 레퍼런스·실 LLM·프론트 assembleScene과 동일한 {x,y,w,h} 객체 형식.
    # (이전 배열 [x1,y1,x2,y2] 코너 형식은 프론트가 s.bbox.x로 읽어 좌표가 전부
    #  undefined가 되는 버그를 유발 → 텍스트가 원점에 겹치고 배경이 안 채워졌다.)
    # 좌표는 1080×1350 캔버스 기준(헤드라인/바디=상단, CTA/고지=하단).
    "slots": [
        {"role": "background", "bbox": {"x": 0, "y": 0, "w": 1080, "h": 1350}, "z": 0, "copy_key": None},
        {"role": "logo", "bbox": {"x": 80, "y": 48, "w": 160, "h": 56}, "z": 3, "copy_key": None},
        {"role": "headline", "bbox": {"x": 80, "y": 160, "w": 920, "h": 200}, "z": 1, "copy_key": "headline", "font_px": 72, "color": "#0B1324"},
        {"role": "body", "bbox": {"x": 80, "y": 400, "w": 920, "h": 300}, "z": 1, "copy_key": "body", "font_px": 34, "color": "#1A2332"},
        {"role": "cta", "bbox": {"x": 80, "y": 1150, "w": 460, "h": 110}, "z": 2, "copy_key": "cta", "font_px": 30, "color": "#FFFFFF"},
        # 고지 글자 26px = 최대(72)의 36% ≥ 30%(금투협 §5④), 대비 #3A3A3A/#F2EFE9 ≈ 9:1 ≥ 4.5(WCAG) → 적법.
        {"role": "disclosure", "bbox": {"x": 80, "y": 1276, "w": 920, "h": 58}, "z": 3, "copy_key": "disclosure", "font_px": 26, "color": "#3A3A3A"},
    ],
    "copy": {},
}

# 모든 수치(3.5 / 12 / 100)는 FACTSHEET에 존재 → grounding 통과.
# en/vi/zh는 한글 0(단위어 현지화: 개월→months/tháng/个月, 만원→vạn won/万韩元). 숫자만 유지.
COPY = {
    "ko": {"headline": "연 3.5% JB 정기예금", "body": "12개월 만기, 100만원부터 시작하세요.", "cta": "지금 가입하기"},
    "en": {"headline": "JB Term Deposit at 3.5%", "body": "12-month term. Open online in minutes.", "cta": "Open now"},
    "vi": {"headline": "JB Tiết kiệm 3.5%", "body": "Kỳ hạn 12 tháng, từ 100 vạn won.", "cta": "Mở ngay"},
    "zh": {"headline": "JB定期存款 3.5%", "body": "12个月期限，100万韩元起。", "cta": "立即开户"},
}

# 시연 핵심 — Design 1차 산출에 의도적으로 끼우는 위반 카피(ko만).
#   headline = 과장광고(업계 최고/최고 금리, 객관적 근거 없는 최상급) → 표시광고법 §3
#   body     = 금리 불일치(연 4.0% ≠ 마스터 3.5%) + 우대조건 단서(세전/우대) 누락
# R1 법률 검토가 콘텐츠 기반으로 적발(critical 2 + warning 1) → 검토 BLOCKED.
# en/vi/zh는 clean(COPY와 동일) — 위반은 ko에 집중하고, #4(vi/zh 예금자보호 고지
# 누락)는 harness_design.DISCLOSURE_DISPLAY로 별도 스테이징한다.
# 교정(FabricEditor 씬 수동 편집)으로 위반 토큰이 사라지면 재검토 PASS(위반→교정 루프).
COPY_VIOLATING = {
    "ko": {"headline": "업계 최고 금리 JB 정기예금",
           "body": "연 4.0% 12개월 만기, 100만원부터 시작하세요.",
           "cta": "지금 가입하기"},
    "en": dict(COPY["en"]),
    "vi": dict(COPY["vi"]),
    "zh": dict(COPY["zh"]),
}

CRITIC_SCORES = {
    "hierarchy": 4, "grid": 4, "whitespace": 4, "cta": 4,
    "compliance": 5, "copy_visual": 4, "brand": 4,
}

# Stage A 1턴 리서치 인용 — 캠페인 의사결정 근거(공식 출처). 하네스 _save_research가
# assets/research/article/src_N.md로 저장 → 파일 트리에 리서치 산출물로 노출.
# 스니펫은 이후 단계의 핵심(3.5% 금리·예금자보호 5천만원·우대/세전 고지)과 연결된다.
RESEARCH_CITATIONS = [
    {"url": "https://www.bok.or.kr/portal/main/main.do",
     "title": "한국은행 예금금리 동향",
     "snippet": "2030 세대의 정기예금 신규 가입이 증가세이며 금리 민감도가 높음. "
                "모바일·비대면 채널 비중이 큼."},
    {"url": "https://www.kdic.or.kr/protect/protect_system.do",
     "title": "예금자보호제도 — 예금보험공사",
     "snippet": "예금자보호법에 따라 1인당 원금과 이자를 합하여 5천만원까지 보호된다. "
                "금융 광고에 보호 한도 고지 권장."},
    {"url": "https://www.fsc.go.kr/po040301",
     "title": "금융광고 규제 가이드 — 금융위원회",
     "snippet": "금리·수익률 표시 시 세전 여부와 우대조건을 명확히 고지해야 하며, "
                "객관적 근거 없는 '업계 최고' 등 최상급 표현은 표시광고법 위반 소지."},
]

# Stage B 1차 plan 초안 — 필수 요소 중 disclosures·slots가 빠진 미완성본(의도적).
# 하네스 critic이 누락을 적발 → 'c' 보충 질문 → 사용자가 보강하면 PLAN_MD(완성)로 교체.
# (인터랙티브 기획: 1차 누락 → 2차 완성 흐름을 시연)
PLAN_MD_PARTIAL = """---
creative_direction:
  palette: ["#00857C", "#0B2B5B", "#FFFFFF"]
  font: Pretendard
  grid: 12col
  aspect: "4:5"
material_matrix: [{channel: instagram, format: square}, {channel: email, format: banner}]
image_concept: 밝은 톤의 추상적 금융 성장 이미지
copy_themes: [높은 금리, 간편 가입, 신뢰]
multinational: true
languages: [ko, en, vi, zh]
factsheet:
  product: JB 정기예금
  interest_rate: 3.5%
  term: 12개월
  min_amount: 100만원
---
# 구현 계획 (초안)

레이아웃·카피·비주얼 방향을 잡았습니다. 컴플라이언스 고지와 슬롯 정의를 보강해야 합니다.
"""

VIDEO_PLAN_MD = """---
medium: video
video_direction:
  duration_sec: 15
  aspect: "9:16"
  fps: 30
  pacing: medium
  palette: ["#0B2B5B", "#00857C", "#FFFFFF"]
  font: Pretendard
  music: uplifting
  voiceover: false
footage_concept: 밝은 톤의 추상적 금융 성장 모션 배경
scene_beats: [훅, 혜택, 신뢰, CTA]
copy_themes: [높은 금리, 간편 가입, 신뢰]
multinational: true
languages: [ko, en, vi, zh]
material_matrix: [{channel: instagram, format: reels, aspect: "9:16", duration: 15}]
factsheet:
  product: JB 정기예금
  interest_rate: 3.5%
  term: 12개월
  min_amount: 100만원
disclosures: [예금자보호법에 따라 5천만원까지 보호]
---
# 영상 구현 계획

훅→혜택(3.5%)→신뢰(예금자보호)→CTA 4비트, 9:16 15초 릴스.
"""

STORYBOARD_SPEC = {
    "aspect": "9:16", "duration_sec": 15, "fps": 30, "bg_color": "#0B2B5B",
    "shots": [
        {"id": "s1", "start": 0.0, "end": 4.0,
         "footage_prompt": "추상적 금융 성장, 밝은 톤, 텍스트 없음",
         "camera": "slow zoom-in", "transition_in": "fade", "transition_out": "cut",
         "layers": [{"role": "headline", "copy_key": "headline", "in": 0.5, "out": 3.8,
                     "anim": "rise-fade", "font_px": 96, "color": "#FFFFFF",
                     "bbox": {"x": 80, "y": 300, "w": 900, "h": 220}}]},
        {"id": "s2", "start": 4.0, "end": 8.0, "footage_prompt": "동전·그래프 상승 모션, 텍스트 없음",
         "camera": "pan-right", "transition_in": "cut", "transition_out": "cut",
         "layers": [{"role": "body", "copy_key": "body", "in": 4.3, "out": 7.8,
                     "anim": "fade", "font_px": 48, "color": "#FFFFFF",
                     "bbox": {"x": 80, "y": 400, "w": 900, "h": 180}}]},
        {"id": "s3", "start": 8.0, "end": 11.0, "footage_prompt": "안정감 있는 금고 모션, 텍스트 없음",
         "camera": "static", "transition_in": "cut", "transition_out": "cut", "layers": []},
        {"id": "s4", "start": 11.0, "end": 15.0, "footage_prompt": "브랜드 컬러 배경, 텍스트 없음",
         "camera": "static", "transition_in": "fade", "transition_out": "fade",
         "layers": [
             {"role": "cta", "copy_key": "cta", "in": 11.2, "out": 15.0, "anim": "pop",
              "font_px": 56, "color": "#FFFFFF", "bbox": {"x": 80, "y": 700, "w": 900, "h": 160}},
             {"role": "disclosure", "copy_key": "disclosure", "in": 11.0, "out": 15.0,
              "font_px": 30, "color": "#E8E8E8", "bbox": {"x": 80, "y": 1700, "w": 900, "h": 120}}]},
    ],
    "copy": {},
    "audio": {"music": "uplifting", "voiceover": False},
}


def _png_chunk(typ: bytes, data: bytes) -> bytes:
    body = typ + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def placeholder_png(width: int = 512, height: int = 512, rgb: tuple = (0, 133, 124)) -> bytes:
    """의존 없이 단색(JB 그린) PNG 생성 — 배경 에셋 부재 시 폴백."""
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    row = b"\x00" + bytes(rgb) * width
    raw = row * height
    idat = zlib.compress(raw, 9)
    return sig + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", idat) + _png_chunk(b"IEND", b"")


_POSTER_BG = os.path.join(os.path.dirname(__file__), "..", "references", "design", "poster_bg.png")


def load_poster_bg() -> bytes:
    """시연용 배경 비주얼(사용자 제공, 텍스트-free 4:5 금융 배경) 바이트.

    Design S2a가 배경으로 사용 → Fabric 씬에서 헤드라인/바디/CTA/고지가 레이어로 얹힌다.
    파일 부재 시 그라데이션 placeholder로 graceful 폴백(키 없이도 안전).
    """
    try:
        with open(_POSTER_BG, "rb") as f:
            return f.read()
    except OSError:
        return placeholder_png()
