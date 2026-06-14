"""Video 렌더 서비스 — 확정 storyboard → ffmpeg → review/_render/final.mp4 (spec §5).

순수 빌더(spec→ffmpeg argv)와 오케스트레이터(render_video)를 분리한다. 모든 빌더는
ffmpeg 바이너리 없이 결정론적으로 테스트된다. 렌더 전 고지 ≥3초를 evaluate_timing으로
서버 재검증(프론트와 이중) — 위반 시 ComplianceError(→ 라우터에서 422).
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .scoring import evaluate_timing

logger = logging.getLogger(__name__)

STORYBOARD_PATH = "/{run_id}/video/storyboard/storyboard.spec.json"


class ComplianceError(Exception):
    """렌더 전 컴플라이언스 위반(고지 노출시간 등) — 라우터가 422로 매핑."""


def load_storyboard(store, run_id: str) -> dict:
    """VFS의 확정 storyboard.spec.json 로드(프론트가 편집본을 PUT한 상태)."""
    text = store.get_text(STORYBOARD_PATH.format(run_id=run_id))
    if not text:
        raise ComplianceError("storyboard.spec.json이 없습니다 — 콘티 확정 후 렌더하세요.")
    return json.loads(text)


def assert_render_compliance(storyboard: dict, lang: str = "ko") -> None:
    """렌더 전 결정론 컴플라이언스 게이트. 위반 시 ComplianceError(증거 메시지).

    1) 고지 노출시간 ≥ DISCLOSURE_MIN_SEC(evaluate_timing). 2) 해당 언어 고지 문구가
    실제로 존재(타이밍만 통과하고 copy가 비면 화면에 고지가 안 떠 무의미·위험).
    """
    viols = evaluate_timing(storyboard)
    if viols:
        raise ComplianceError("; ".join(v.get("evidence", v.get("rule", "")) for v in viols))
    copy = (storyboard.get("copy") or {}).get(lang, {}) or {}
    has_text = False
    for shot in storyboard.get("shots", []) or []:
        for layer in shot.get("layers", []) or []:
            if layer.get("role") == "disclosure":
                key = layer.get("copy_key") or "disclosure"
                if str(copy.get(key, "")).strip():
                    has_text = True
    if not has_text:
        raise ComplianceError(
            f"고지 문구({lang})가 비어 있어 렌더할 수 없습니다 — 고지 텍스트를 확정하세요.")
    return None


def escape_drawtext(s: str) -> str:
    """ffmpeg drawtext text= 값 이스케이프(백슬래시·콜론·작은따옴표). argv 전달이라 셸은 무관."""
    return s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _ff_color(c: str) -> str:
    """ffmpeg 색상 표기 — '#RRGGBB' → '0xRRGGBB', 그 외(명명색)는 그대로."""
    c = (c or "").strip()
    if c.startswith("#"):
        return "0x" + c[1:]
    return c or "white"


def build_drawtext_filters(storyboard: dict, lang: str, *, font_path: str | None) -> list[str]:
    """각 레이어 → drawtext 필터 문자열. 문구 없는 레이어는 스킵. in/out=절대시간."""
    copy = (storyboard.get("copy") or {}).get(lang, {}) or {}
    out: list[str] = []
    for shot in storyboard.get("shots", []) or []:
        for layer in shot.get("layers", []) or []:
            key = layer.get("copy_key") or layer.get("role")
            text = copy.get(key, "")
            if not text:
                continue
            bbox = layer.get("bbox", {}) or {}
            font = f"fontfile='{font_path}':" if font_path else ""
            out.append(
                # expansion=none: '%'·'{'·'}'를 리터럴로(금리 "3.5%" 등 깨짐·치환 주입 방지)
                "drawtext=" + font + "expansion=none:"
                + f"text='{escape_drawtext(str(text))}'"
                + f":fontsize={int(layer.get('font_px', 48))}"
                + f":fontcolor={_ff_color(layer.get('color', '#FFFFFF'))}"
                + f":x={int(bbox.get('x', 0))}:y={int(bbox.get('y', 0))}"
                + f":enable='between(t,{float(layer.get('in', 0))},{float(layer.get('out', 0))})'"
            )
    return out


@dataclass
class Segment:
    """샷 1개의 렌더 소스. kind: 'video'|'image'|'color'. color는 kind=='color'일 때만."""
    kind: str
    path: str | None
    dur: float
    color: str | None = None


def build_filter_complex(segments: list["Segment"], drawtext: list[str], *,
                         w: int, h: int, fps: int) -> str:
    """세그먼트 정규화(scale/crop/setsar/trim) → concat[base] → drawtext 체인 → [vout]."""
    parts: list[str] = []
    labels: list[str] = []
    for i, seg in enumerate(segments):
        # 모든 입력을 동일 해상도·SAR·fps로 정규화 후 길이 고정(trim) → concat 정합.
        # fps 통일 누락 시 image2(기본 25fps)와 lavfi/video가 섞여 concat 타임스탬프 깨짐.
        f = (f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
             f"crop={w}:{h},setsar=1,fps={fps},"
             f"trim=duration={seg.dur},setpts=PTS-STARTPTS[v{i}]")
        parts.append(f)
        labels.append(f"[v{i}]")
    parts.append("".join(labels) + f"concat=n={len(segments)}:v=1:a=0[base]")
    if drawtext:
        cur = "base"
        for j, d in enumerate(drawtext):
            nxt = "vout" if j == len(drawtext) - 1 else f"t{j}"
            parts.append(f"[{cur}]{d}[{nxt}]")
            cur = nxt
    else:
        parts.append("[base]null[vout]")
    return ";".join(parts)


def build_ffmpeg_command(segments: list["Segment"], drawtext: list[str], *,
                         out_path: str, w: int, h: int, fps: int,
                         music_path: str | None) -> list[str]:
    """단일 ffmpeg argv(셸 없음). image=loop, color=lavfi, video=직접 입력. 음악=stream_loop+map."""
    argv: list[str] = ["ffmpeg", "-y"]
    for seg in segments:
        if seg.kind == "image":
            argv += ["-loop", "1", "-t", str(seg.dur), "-i", seg.path]
        elif seg.kind == "color":
            argv += ["-f", "lavfi", "-t", str(seg.dur),
                     "-i", f"color=c={_ff_color(seg.color or '#000000')}:s={w}x{h}:r={fps}"]
        else:  # video
            argv += ["-i", seg.path]
    music_idx = None
    if music_path:
        music_idx = len(segments)
        argv += ["-stream_loop", "-1", "-i", music_path]
    argv += ["-filter_complex", build_filter_complex(segments, drawtext, w=w, h=h, fps=fps)]
    argv += ["-map", "[vout]"]
    if music_idx is not None:
        argv += ["-map", f"{music_idx}:a", "-c:a", "aac", "-shortest"]
    argv += ["-r", str(fps), "-c:v", "libx264", "-pix_fmt", "yuv420p", out_path]
    return argv


# 의존 없는 최소 mp4 시그니처(fake provider와 동일) — ffmpeg 부재/실패 시 결정론 stub.
STUB_MP4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"

_AUTO = object()   # render_video(ffmpeg=...) 기본 — env+which 자동 해석 sentinel

RENDER_PATH = "/{run_id}/review/_render/final.mp4"
FOOTAGE_PATH = "/{run_id}/video/design-system/components/footage/clip_{sid}.mp4"

# fonts-noto-cjk(Dockerfile) 설치 경로. env override 우선.
_FONT_CANDIDATES = (
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
)


def _resolve_ffmpeg(override):
    """ffmpeg 경로 해석. _AUTO=env+which, None=강제 stub, str=그대로."""
    if override is None:
        return None
    if override is not _AUTO:
        return override
    if os.environ.get("MARKER_DISABLE_FFMPEG"):
        return None
    return shutil.which("ffmpeg")


def _resolve_font() -> str | None:
    p = os.environ.get("MARKER_CJK_FONT")
    if p and Path(p).exists():
        return p
    for c in _FONT_CANDIDATES:
        if Path(c).exists():
            return c
    # 패키지 레이아웃 변형(파일명·경로) 방어: fonts 트리에서 Noto CJK/KR 글롭.
    for root in ("/usr/share/fonts", "/usr/local/share/fonts"):
        base = Path(root)
        if not base.exists():
            continue
        for pat in ("**/NotoSansCJK*.ttc", "**/NotoSansCJK*.otf",
                    "**/NotoSansKR*.otf", "**/NotoSansKR*.ttf",
                    "**/NotoSerifCJK*.ttc"):
            hits = sorted(base.glob(pat))
            if hits:
                return str(hits[0])
    return None


def _resolve_music() -> str | None:
    """backend/assets/music/bed.* 드롭인(미커밋 — README 참조). 없으면 무음."""
    base = Path(__file__).resolve().parents[3] / "assets" / "music"
    for ext in ("m4a", "mp3", "wav", "aac", "ogg"):
        f = base / f"bed.{ext}"
        if f.exists():
            return str(f)
    return None


# footage 바이트 매직 — 데모/폴백이 still(PNG/JPEG)을 video/mp4로 오표기하는 경우 방어.
_IMAGE_MAGICS = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff")


def _looks_like_image(blob: bytes) -> bool:
    return any(blob.startswith(m) for m in _IMAGE_MAGICS)


def _build_segments(store, run_id: str, storyboard: dict, tmpdir: str,
                    *, w: int, h: int) -> list["Segment"]:
    """샷별 footage 노드 → Segment. video/image=temp 파일로 구현화, 누락/실패=color."""
    bg = storyboard.get("bg_color") or "#000000"
    segs: list[Segment] = []
    for shot in storyboard.get("shots", []) or []:
        sid = shot.get("id")
        dur = max(0.1, float(shot.get("end", 0)) - float(shot.get("start", 0)))
        node = store.get(FOOTAGE_PATH.format(run_id=run_id, sid=sid))
        blob = getattr(node, "blob", None) if node else None
        if not blob:
            segs.append(Segment(kind="color", path=None, dur=dur, color=bg))
            continue
        mime = (node.mime or (node.meta or {}).get("mime") or "")
        # 바이트 매직 우선: demo/폴백이 still을 video/mp4로 오표기 → 실 ffmpeg 디코드 실패
        # → 항상 stub로 폴백하던 버그(C1) 방어. 매직이 이미지면 mime 무시하고 image로.
        if _looks_like_image(blob):
            kind = "image"
        elif "video" in mime:
            kind = "video"
        else:
            kind = "image"
        ext = ".mp4" if kind == "video" else ".png"
        fp = Path(tmpdir) / f"{sid}{ext}"
        fp.write_bytes(blob)
        segs.append(Segment(kind=kind, path=str(fp), dur=dur))
    return segs


def render_video(store, run_id: str, *, lang: str = "ko", ffmpeg=_AUTO) -> str:
    """확정 storyboard → review/_render/final.mp4. 위반 시 ComplianceError. 산출 경로 반환.

    ffmpeg 부재/실패 시 결정론 stub mp4로 폴백(데모·CI가 ffmpeg 없이 동작).
    """
    storyboard = load_storyboard(store, run_id)
    assert_render_compliance(storyboard, lang)       # 위반 시 ComplianceError(산출 전)

    out_path = RENDER_PATH.format(run_id=run_id)
    w, h = 1080, 1920
    fps = int(storyboard.get("fps", 30) or 30)
    ffmpeg_bin = _resolve_ffmpeg(ffmpeg)

    data = STUB_MP4
    render_error: str | None = None
    if ffmpeg_bin:
        with tempfile.TemporaryDirectory() as td:
            segs = _build_segments(store, run_id, storyboard, td, w=w, h=h)
            if segs:
                dt = build_drawtext_filters(storyboard, lang, font_path=_resolve_font())
                local_out = str(Path(td) / "final.mp4")
                argv = build_ffmpeg_command(segs, dt, out_path=local_out,
                                            w=w, h=h, fps=fps, music_path=_resolve_music())
                argv[0] = ffmpeg_bin
                try:
                    subprocess.run(argv, check=True, capture_output=True, timeout=600)
                    rendered = Path(local_out).read_bytes()
                    if rendered:
                        data = rendered
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
                    # stderr·argv 로깅 — 부재 시 배포에서 렌더 실패가 블랙박스(C2).
                    stderr = getattr(e, "stderr", b"") or b""
                    if isinstance(stderr, str):
                        stderr = stderr.encode("utf-8", "replace")
                    logger.warning("ffmpeg 렌더 실패(%s) → stub 폴백. argv=%s stderr=%s",
                                   type(e).__name__, " ".join(argv),
                                   stderr[-2000:].decode("utf-8", "replace"))
                    render_error = type(e).__name__
                    data = STUB_MP4                  # ffmpeg 실패 → stub 폴백(렌더 비차단)
    meta = {"type": "video", "source": "marker", "mime": "video/mp4",
            "render": "ffmpeg" if (ffmpeg_bin and data is not STUB_MP4) else "stub",
            "lang": lang}
    if render_error:
        meta["render_error"] = render_error
    store.put(out_path, data, source="marker", mime="video/mp4", meta=meta)
    return out_path
