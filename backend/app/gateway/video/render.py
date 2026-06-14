"""Video 렌더 서비스 — 확정 storyboard → ffmpeg → review/_render/final.mp4 (spec §5).

순수 빌더(spec→ffmpeg argv)와 오케스트레이터(render_video)를 분리한다. 모든 빌더는
ffmpeg 바이너리 없이 결정론적으로 테스트된다. 렌더 전 고지 ≥3초를 evaluate_timing으로
서버 재검증(프론트와 이중) — 위반 시 ComplianceError(→ 라우터에서 422).
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from .scoring import evaluate_timing

STORYBOARD_PATH = "/{run_id}/video/storyboard/storyboard.spec.json"


class ComplianceError(Exception):
    """렌더 전 컴플라이언스 위반(고지 노출시간 등) — 라우터가 422로 매핑."""


def load_storyboard(store, run_id: str) -> dict:
    """VFS의 확정 storyboard.spec.json 로드(프론트가 편집본을 PUT한 상태)."""
    text = store.get_text(STORYBOARD_PATH.format(run_id=run_id))
    if not text:
        raise ComplianceError("storyboard.spec.json이 없습니다 — 콘티 확정 후 렌더하세요.")
    return json.loads(text)


def assert_render_compliance(storyboard: dict) -> None:
    """렌더 전 결정론 컴플라이언스 게이트. 위반 시 ComplianceError(증거 메시지)."""
    viols = evaluate_timing(storyboard)
    if viols:
        raise ComplianceError("; ".join(v.get("evidence", v.get("rule", "")) for v in viols))
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
                "drawtext=" + font
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
        f = f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1"
        if seg.kind == "video":
            f += f",trim=duration={seg.dur},setpts=PTS-STARTPTS"
        else:
            f += ",setpts=PTS-STARTPTS"
        f += f"[v{i}]"
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
