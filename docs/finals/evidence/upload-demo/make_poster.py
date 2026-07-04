"""데모용 '외부 업로드 포스터' 생성 — 가상 저축은행 홍보물에 표시광고법 위반 문구 심음.
'원금 100% 보장'을 정규화 bbox {0.08,0.34,0.84,0.11}(캔버스 1080×1350) 영역에 배치 →
UPLOAD_HIGHLIGHT_BBOX authored 값과 정렬. 1회 실행해 PNG 생성·커밋."""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
BBOX = {"x": 0.08, "y": 0.34, "w": 0.84, "h": 0.11}   # '원금 100% 보장'


def _font(px, bold=True):
    for p in ("C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf",
              "/usr/share/fonts/opentype/noto/NotoSansCJKkr-Bold.otf"):
        try:
            return ImageFont.truetype(p, px)
        except Exception:
            continue
    return ImageFont.load_default()


def _centered(d, box, text, font, fill):
    x0, y0, x1, y1 = box
    tb = d.textbbox((0, 0), text, font=font)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    d.text((x0 + (x1 - x0 - tw) / 2 - tb[0], y0 + (y1 - y0 - th) / 2 - tb[1]), text, font=font, fill=fill)


def main():
    im = Image.new("RGB", (W, H), (11, 41, 74))
    d = ImageDraw.Draw(im)
    for y in range(H):  # 세로 그라데이션(네이비→틸)
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(11 + 8 * t), int(41 + 70 * t), int(74 + 60 * t)))
    _centered(d, (80, 70, 1000, 150), "믿음저축은행", _font(48), (255, 255, 255))
    _centered(d, (80, 165, 1000, 220), "정기예금 특판 · 신규 고객 한정", _font(30, False), (200, 225, 255))
    # 위반 문구 — bbox 영역에 정확히 배치
    bx = (BBOX["x"] * W, BBOX["y"] * H, (BBOX["x"] + BBOX["w"]) * W, (BBOX["y"] + BBOX["h"]) * H)
    _centered(d, bx, "원금 100% 보장", _font(96), (255, 214, 77))
    _centered(d, (80, 640, 1000, 740), "확정 수익 연 8.5%", _font(72), (255, 255, 255))
    _centered(d, (80, 780, 1000, 840), "누구나 무조건 최고 금리 · 손실 걱정 없이", _font(34, False), (220, 235, 255))
    d.rounded_rectangle((300, 980, 780, 1080), radius=16, fill=(255, 214, 77))
    _centered(d, (300, 980, 780, 1080), "지금 가입하기", _font(40), (11, 41, 74))
    _centered(d, (80, 1250, 1000, 1300),
              "※ 본 광고는 예시입니다. 실제 상품과 무관.", _font(20, False), (150, 175, 205))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "external-deposit-promo.png")
    im.save(out)
    print("WROTE", out, im.size, "bbox", BBOX)


if __name__ == "__main__":
    main()
