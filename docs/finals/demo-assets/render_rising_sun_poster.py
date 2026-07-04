"""데모 픽스처 렌더: 욱일기(방사형 햇살)가 '게슴츠레' 섞인 금융 프로모션 포스터.

RC(논란) 검토의 시각 심볼 탐지를 시연하기 위한 테스트 소재. 실제 브랜드들이
'일출/햇살' 디자인에 무심코 욱일기 방사선을 넣어 논란 난 패턴을 재현한다.
결정론 렌더(PIL) — Windows 맑은고딕. `python render_rising_sun_poster.py [alpha]`.

출력: 2026-신년-해돋이-적금.png (이 파일을 Review에 업로드하면 mock이 파일명
'해돋이' 트리거로 욱일기 논란(other_sensitive·critical)을 결정론 적발한다.
라이브 비전은 파일명과 무관하게 실제 도안을 탐지 — mock은 그 경로의 결정론 재현).
"""
import math
import sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
CREAM = (251, 246, 236, 255)
NAVY = (11, 42, 91, 255)
RED = (200, 46, 46)
GOLD = (196, 152, 66, 255)

RAY_ALPHA = int(sys.argv[1]) if len(sys.argv) > 1 else 40   # 게슴츠레(은은) 기본
N_RAYS = 16                  # 욱일기 정통 16선
SUN_CX, SUN_CY, SUN_R = 540, 430, 115

FONT_DIR = "C:/Windows/Fonts/"
def font(name, size):
    try:
        return ImageFont.truetype(FONT_DIR + name, size)
    except Exception:
        return ImageFont.load_default()

f_kicker = font("malgun.ttf", 33)
f_head   = font("malgunbd.ttf", 150)
f_sub    = font("malgun.ttf", 44)
f_rate   = font("malgunbd.ttf", 88)
f_cta    = font("malgunbd.ttf", 48)
f_foot   = font("malgun.ttf", 24)

img = Image.new("RGBA", (W, H), CREAM)

# ── 욱일기 방사형 햇살(게슴츠레) — 별도 RGBA 레이어에 그려 합성 ──
rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))
rd = ImageDraw.Draw(rays)
R = 1700
half = math.radians(360 / N_RAYS / 2 * 0.86)
for k in range(N_RAYS):
    a = math.radians(k * 360 / N_RAYS - 90)
    p1 = (SUN_CX + R * math.cos(a - half), SUN_CY + R * math.sin(a - half))
    p2 = (SUN_CX + R * math.cos(a + half), SUN_CY + R * math.sin(a + half))
    rd.polygon([(SUN_CX, SUN_CY), p1, p2], fill=RED + (RAY_ALPHA,))
rd.ellipse([SUN_CX - SUN_R, SUN_CY - SUN_R, SUN_CX + SUN_R, SUN_CY + SUN_R],
           fill=RED + (int(RAY_ALPHA * 1.9),))
img = Image.alpha_composite(img, rays)

dr = ImageDraw.Draw(img)
def center(txt, y, fnt, fill):
    dr.text(((W - dr.textlength(txt, font=fnt)) / 2, y), txt, font=fnt, fill=fill)

def pill(txt, cy, fnt, fill_bg, fill_fg, pad_x=48, pad_y=14):
    """텍스트 폭에 맞춰 자동 크기 알약 배지(넘침 방지)."""
    tw = dr.textlength(txt, font=fnt)
    asc, desc = fnt.getmetrics()
    th = asc + desc
    x0, x1 = (W - tw) / 2 - pad_x, (W + tw) / 2 + pad_x
    y0, y1 = cy, cy + th + pad_y * 2
    dr.rounded_rectangle([x0, y0, x1, y1], radius=(y1 - y0) / 2, fill=fill_bg)
    dr.text(((W - tw) / 2, y0 + pad_y), txt, font=fnt, fill=fill_fg)
    return y1

center("JB금융그룹 · 2026 신년 특별기획", 120, f_kicker, NAVY)
center("해돋이 적금", 600, f_head, NAVY)
center("새해 첫 햇살처럼 떠오르는 이자", 790, f_sub, NAVY)
pill("최고 연 4.5%", 892, f_rate, NAVY, (255, 255, 255, 255), pad_x=54, pad_y=12)
pill("지금 가입하기", 1120, f_cta, GOLD, NAVY, pad_x=52, pad_y=16)
center("※ 세전 기준·우대조건 충족 시. 예금자보호법에 따라 보호. 상품 시안(데모).",
       1288, f_foot, (120, 120, 120, 255))

out = sys.argv[2] if len(sys.argv) > 2 else "2026-신년-해돋이-적금.png"
img.convert("RGB").save(out, "PNG")
print("SAVED", out, "alpha=", RAY_ALPHA)
