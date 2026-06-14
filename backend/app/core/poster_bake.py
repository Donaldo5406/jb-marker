"""Mock 전용 포스터 베이크 — 텍스트-free 배경에 헤드라인/바디/CTA 카피를 합성한다.

실모드(S2a)는 Gemini가 bake_prompt의 카피를 이미지에 직접 렌더한다. mock의 generate_image는
이미지 모델이 없으므로 이 함수로 **동등한 결과를 결정적으로 재현**한다 — 프롬프트에서 파싱한
언어별 카피를 PIL로 배경에 합성. 배치·휘도 기반 스크림은 frontend sceneAssembler.ts를 포팅했다.

폰트 해석: Noto CJK(배포 Docker: fonts-noto-cjk) → malgun(Windows 시연) → DejaVu → PIL 기본.
한글 폰트가 전혀 없거나 PIL 실패 시 호출부(demo.generate_image)가 배경 원본을 그대로 반환한다.

베이크 대상은 headline/body/cta뿐 — 로고·고지(disclosure)는 frontend가 레이어로 오버레이하므로
(one-layer 모델) 중복을 피해 굽지 않는다.
"""
from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)

# 레퍼런스 캔버스(LAYOUT_SPEC 기준 1080×1350)에서의 슬롯 배치 — 실제 배경 크기로 스케일된다.
_REF_W, _REF_H = 1080, 1350
_SLOTS = [
    {"role": "headline", "x": 80, "y": 150, "w": 920, "h": 220, "px": 76, "color": "#0B1324", "bold": True},
    {"role": "body", "x": 80, "y": 400, "w": 920, "h": 280, "px": 38, "color": "#1A2332", "bold": False},
    {"role": "cta", "x": 80, "y": 1150, "w": 520, "h": 110, "px": 34, "color": "#FFFFFF", "bold": True},
]
_BRAND = (0, 133, 124)  # JB 그린(#00857C) — CTA 버튼 배경

# 폰트 후보(굵게/일반). 앞에서부터 존재하는 첫 파일을 사용.
_FONT_BOLD = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKkr-Bold.otf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "C:/Windows/Fonts/malgunbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
_FONT_REG = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKkr-Regular.otf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "C:/Windows/Fonts/malgun.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _load_font(px: int, bold: bool):
    from PIL import ImageFont
    for path in (_FONT_BOLD if bold else _FONT_REG):
        try:
            return ImageFont.truetype(path, px)
        except OSError:
            continue
    return ImageFont.load_default()


def _rel_lum(hexc: str) -> float:
    n = int(hexc.lstrip("#"), 16)
    r, g, b = ((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _wrap(draw, text: str, font, max_w: int) -> str:
    """공백 기준 단어 래핑 + 명시적 개행 보존. 한 단어가 폭을 넘으면 그대로 둔다."""
    out_lines = []
    for para in (text or "").split("\n"):
        words = para.split(" ")
        line = ""
        for w in words:
            trial = f"{line} {w}".strip()
            if draw.textlength(trial, font=font) <= max_w or not line:
                line = trial
            else:
                out_lines.append(line)
                line = w
        out_lines.append(line)
    return "\n".join(out_lines)


def bake_copy(bg_bytes: bytes, copy: dict, *, aspect: str = "4:5") -> bytes:
    """배경 바이트 + 언어별 copy({headline,body,cta}) → 카피가 합성된 PNG 바이트.

    실패 시 예외를 올린다(호출부가 배경 원본으로 폴백). 폰트 부재만으로는 실패하지 않으며
    PIL 기본 폰트로라도 그린다(영문 데모는 가독, 한글은 폰트 있을 때만 정상).
    """
    from PIL import Image, ImageDraw

    img = Image.open(io.BytesIO(bg_bytes)).convert("RGBA")
    W, H = img.size
    sx, sy = W / _REF_W, H / _REF_H
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    pad = max(8, int(W * 0.012))

    for slot in _SLOTS:
        text = (copy or {}).get(slot["role"], "")
        if not text:
            continue
        px = max(12, int(slot["px"] * sx))
        font = _load_font(px, slot["bold"])
        x, y = int(slot["x"] * sx), int(slot["y"] * sy)
        max_w = int(slot["w"] * sx)
        wrapped = _wrap(d, text, font, max_w)
        spacing = int(px * 0.28)
        bbox = d.multiline_textbbox((x, y), wrapped, font=font, spacing=spacing)
        rect = [bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad]
        if slot["role"] == "cta":
            d.rounded_rectangle(rect, radius=int(pad * 1.8), fill=_BRAND + (245,))
        else:
            # 휘도 기반 스크림: 어두운 글자 → 밝은 스크림, 밝은 글자 → 어두운 스크림(가독 보장).
            scrim = (255, 255, 255, 150) if _rel_lum(slot["color"]) <= 0.5 else (0, 0, 0, 110)
            d.rounded_rectangle(rect, radius=pad, fill=scrim)
        d.multiline_text((x, y), wrapped, font=font, fill=slot["color"], spacing=spacing)

    out = Image.alpha_composite(img, overlay).convert("RGB")
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()
