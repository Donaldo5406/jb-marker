"""design-system(tokens + 컴포넌트 카탈로그) → self-contained HTML 프리뷰.

이미지는 base64 data URI로 인라인 → iframe이 네트워크 요청 0(인증·CORS 무관).
tokens.json 없으면 안내 HTML 반환(200, 빈 프리뷰). 캐시 없음(on-demand).

NOTE: ``store.get()``은 blob_path가 있으면 바이트를 ``node.blob``으로 지연
로드한다(LocalVfsStore·SupabaseVfsStore 공통). 비주얼 인라인은 ``node.blob``을
우선 사용하고, 비어 있으면 ``blob_path``에서 직접 디스크 로드로 폴백한다.
"""
from __future__ import annotations

import base64
import html
import json
from pathlib import Path

from ..core.fonts import looks_like_font_name

_COPY_ROLES = ["headline", "body", "cta", "disclosure"]
_ROLE_LABELS = {"headline": "헤드라인", "body": "바디", "cta": "CTA", "disclosure": "고지"}


def _esc(v) -> str:
    return html.escape(str(v if v is not None else ""))


def _empty_html() -> str:
    return (
        "<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
        "<style>body{font-family:Inter,system-ui,sans-serif;margin:0;"
        "display:flex;align-items:center;justify-content:center;height:100vh;"
        "color:#64748b;background:#f8fafc}</style></head><body>"
        "<p>디자인 단계가 아직 완료되지 않았습니다.</p></body></html>"
    )


def _blob_bytes(node) -> bytes:
    """노드의 바이너리 바이트(get()이 채운 .blob 우선, 없으면 blob_path 디스크 로드)."""
    raw = getattr(node, "blob", None)
    if raw:
        return raw
    blob_path = getattr(node, "blob_path", None)
    if blob_path:
        try:
            return Path(blob_path).read_bytes()
        except OSError:
            return b""
    return b""


def _downscale_inline(raw: bytes, mime: str | None, *, max_dim: int = 640) -> tuple[bytes, str]:
    """비주얼을 썸네일(JPEG)로 다운스케일해 base64 인라인 크기를 줄인다.

    풀해상도 키비주얼(실 Nano Banana는 1MB+)을 그대로 인라인하면 프리뷰 HTML이
    수 MB가 되어 iframe srcdoc 다운로드·렌더가 수초 지연된다(History에서 프리뷰가
    "안 뜨는" 체감의 실제 원인). Pillow 미설치·디코드 실패·외려 커짐 시 원본을
    그대로 반환(graceful)한다.
    """
    try:
        from io import BytesIO
        from PIL import Image  # optional dep — 없으면 except로 원본 유지

        im = Image.open(BytesIO(raw))
        im.thumbnail((max_dim, max_dim))
        if im.mode != "RGB":
            # 투명도는 흰 배경에 합성(프리뷰 배경이 밝음)
            rgba = im.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[-1])
            im = bg
        out = BytesIO()
        im.save(out, format="JPEG", quality=82, optimize=True)
        small = out.getvalue()
        if len(small) < len(raw):  # 이미 아주 작은 이미지는 원본 유지
            return small, "image/jpeg"
    except Exception:
        pass
    return raw, (mime or "image/png")


def build_preview_html(run_id: str, store) -> str:
    base = f"/{run_id}/design/design-system"
    tok_node = store.get(f"{base}/tokens.json")
    if tok_node is None or not tok_node.content_text:
        return _empty_html()
    try:
        tokens = json.loads(tok_node.content_text)
    except Exception:
        tokens = {}

    palette = tokens.get("palette") or []
    font = tokens.get("font") or "Inter"
    # 서술형 typography가 font로 새면 CSS font-family가 깨진다. 폰트명일 때만 CSS에 쓰고,
    # 서술형은 타이포 노트(텍스트)로 보존한다(기존 런의 오염된 tokens.font도 안전 처리).
    safe_font = font if looks_like_font_name(font) else "Inter"
    typo_note = tokens.get("typography")
    if not typo_note and not looks_like_font_name(font):
        typo_note = font
    grid = tokens.get("grid")
    aspect = tokens.get("aspect")

    swatches = "".join(
        f"<div class='sw'><span class='chip' style='background:{_esc(c)}'></span>"
        f"<code>{_esc(c)}</code></div>"
        for c in palette
    )

    # 비주얼 base64 인라인 (썸네일 다운스케일로 경량화 — 풀해상도 인라인 시 수 MB).
    visual_html = ""
    vnode = store.get(f"{base}/components/visual/v1.png")
    if vnode is not None:
        raw = _blob_bytes(vnode)
        if raw:
            raw, mime = _downscale_inline(raw, vnode.mime)
            b64 = base64.b64encode(raw).decode("ascii")
            visual_html = (
                f"<img class='visual' alt='visual' "
                f"src='data:{_esc(mime)};base64,{b64}'>"
            )

    # 카피 컴포넌트: 언어별 디렉터리 스캔.
    copy_cards = ""
    comp_nodes = store.list(f"{base}/components/")
    by_role: dict[str, list[tuple[str, str]]] = {r: [] for r in _COPY_ROLES}
    for n in comp_nodes:
        segs = [s for s in n.path.split("/") if s]
        if len(segs) < 2:
            continue
        role = segs[-2]
        lang = segs[-1].replace(".txt", "")
        if role in by_role and n.content_text:
            by_role[role].append((lang, n.content_text))
    for role in _COPY_ROLES:
        for lang, text in sorted(by_role[role]):
            copy_cards += (
                f"<div class='card'><span class='lbl'>{_ROLE_LABELS[role]} · {_esc(lang)}</span>"
                f"<p>{_esc(text)}</p></div>"
            )

    meta_bits = []
    if safe_font:
        meta_bits.append(f"폰트: {_esc(safe_font)}")
    if grid:
        meta_bits.append(f"그리드: {_esc(grid)}")
    if aspect:
        meta_bits.append(f"비율: {_esc(aspect)}")
    meta_line = " · ".join(meta_bits)

    return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'>
<style>
:root{{font-family:{_esc(safe_font)},Inter,system-ui,sans-serif}}
body{{margin:0;padding:24px;background:#f8fafc;color:#0b1324}}
h2{{font-size:14px;text-transform:uppercase;letter-spacing:.05em;color:#64748b;margin:24px 0 8px}}
.meta{{color:#64748b;font-size:13px;margin-bottom:8px}}
.palette{{display:flex;gap:12px;flex-wrap:wrap}}
.sw{{display:flex;flex-direction:column;align-items:center;gap:4px}}
.chip{{width:48px;height:48px;border-radius:8px;border:1px solid rgba(0,0,0,.08);display:block}}
code{{font-size:11px;color:#475569}}
.visual{{max-width:320px;border-radius:12px;border:1px solid rgba(0,0,0,.08)}}
.card{{background:#fff;border:1px solid rgba(0,0,0,.06);border-radius:10px;padding:12px 14px;margin:8px 0}}
.lbl{{font-size:11px;color:#94a3b8;display:block;margin-bottom:4px}}
.card p{{margin:0;font-size:15px}}
.sample{{font-size:28px;font-weight:700;margin:4px 0}}
</style></head><body>
<div class='meta'>{meta_line}</div>
<h2>팔레트</h2><div class='palette'>{swatches}</div>
<h2>타이포</h2><p class='sample'>{_esc(safe_font)}</p><p>본문 샘플 — {_esc(safe_font)}</p>{f"<p class='meta'>{_esc(typo_note)}</p>" if typo_note else ""}
<h2>비주얼</h2>{visual_html or "<p class='meta'>비주얼 없음</p>"}
<h2>카피</h2>{copy_cards or "<p class='meta'>카피 없음</p>"}
</body></html>"""
