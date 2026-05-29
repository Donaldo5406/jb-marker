"""Resize source favicon.png into App Router file-based icons.

Run from frontend/: python scripts/make_favicon.py
Source is the repo-root favicon.png (1254x1254). Outputs app/icon.png (256) and
app/apple-icon.png (180) which Next.js auto-serves as <link rel="icon"> / apple-touch-icon.
"""
from pathlib import Path

from PIL import Image

SRC = Path(r"C:\Users\jgqet\FinAI\favicon.png")
TARGETS = [(256, "app/icon.png"), (180, "app/apple-icon.png")]


def main() -> None:
    im = Image.open(SRC).convert("RGBA")
    for size, name in TARGETS:
        out = Path(name)
        im.resize((size, size), Image.LANCZOS).save(out, optimize=True)
        print(f"{out} -> {size}x{size} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
