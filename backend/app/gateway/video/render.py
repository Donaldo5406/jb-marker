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


# ── 캡션 시네마틱 토큰 ─────────────────────────────────────────────────
# 슬라이드쇼 탈피의 핵심: 텍스트가 footage 위에서 (1) 항상 읽히고 (2) 하드 팝이
# 아니라 부드럽게 등장/퇴장한다. drawtext 식의 콤마는 작은따옴표로 감싸 보호한다
# (enable='between(...)' 와 동일 패턴 — 필터그래프 구분자 콤마와 충돌 방지).
_CAPTION_FADE = 0.4          # 텍스트 페이드 인/아웃 램프(초)
_RISE_PX = 28                # anim "rise" 시작 y 오프셋(아래→제자리)


def _alpha_expr(t_in: float, t_out: float, fade: float = _CAPTION_FADE) -> str:
    """drawtext alpha 식 — [in,in+fade] 페이드인, [out-fade,out] 페이드아웃, 중앙=1.

    삼각 램프 min((t-in)/f, (out-t)/f)를 1로 클램프. 짧은 윗창은 피크<1(여전히 가시).
    """
    i, o, f = f"{t_in:.3f}", f"{t_out:.3f}", f"{max(0.01, fade):.3f}"
    return f"max(0,min(1,min((t-{i})/{f},({o}-t)/{f})))"


def _y_part(y: int, t_in: float, anim: str, fade: float = _CAPTION_FADE) -> str:
    """drawtext y 옵션. rise 계열 anim이면 등장 시 아래→제자리 이징식, 아니면 상수.

    상수 경로는 따옴표 없이 `:y=300`을 유지(리터럴 — 콘티 bbox 회귀 안정).
    """
    if anim and "rise" in anim:
        i, f = f"{t_in:.3f}", f"{max(0.01, fade):.3f}"
        return f":y='{int(y)}+{_RISE_PX}*max(0,1-(t-{i})/{f})'"
    return f":y={int(y)}"


def _fontfile_opt(font_path: str | None) -> str:
    """drawtext fontfile 옵션(작은따옴표). 배포(Linux) 폰트 경로는 콜론이 없어 안전.

    (참고) Windows 드라이브 콜론 'C:'는 필터그래프 옵션 파서가 끊어 로컬 렌더가
    실패하므로, 로컬 검증 시에는 폰트 디렉터리를 cwd로 두고 상대 파일명을 쓴다.
    """
    return f"fontfile='{font_path}':" if font_path else ""


def _caption_deco(role: str | None) -> str:
    """역할별 가독 장식. disclosure(작은 법정고지)=박스 스크림, 그 외=그림자+외곽선.

    헤드라인/CTA는 떠 있는 느낌을 위해 박스 대신 드롭섀도+얇은 외곽선으로 어떤
    배경 위에서도 분리되게 한다. 고지는 복잡한 footage 위에서도 100% 읽혀야 하므로
    반투명 박스 스크림으로 대비를 강제한다.
    """
    if role == "disclosure":
        return ("box=1:boxcolor=black@0.55:boxborderw=18:"
                "borderw=1:bordercolor=black@0.6:")
    return "shadowcolor=black@0.6:shadowx=0:shadowy=3:borderw=2:bordercolor=black@0.85:"


def build_drawtext_filters(storyboard: dict, lang: str, *, font_path: str | None,
                           shot_offsets: list[float] | None = None) -> list[str]:
    """각 레이어 → drawtext 필터 문자열. 문구 없는 레이어는 스킵. in/out=절대시간.

    각 캡션은 역할별 스크림/그림자(_caption_deco) + alpha 페이드(_alpha_expr) +
    anim rise 이징(_y_part)으로 시네마틱하게 등장한다.

    shot_offsets[k]가 주어지면 샷 k의 모든 레이어 in/out을 그만큼 당긴다(크로스페이드로
    압축된 출력 타임라인에 정렬). 레이어는 샷 내부라 in/out을 동일 오프셋만큼 빼므로
    노출 길이(out-in)는 보존된다 → 고지 ≥3초 컴플라이언스 무결성 유지.
    """
    copy = (storyboard.get("copy") or {}).get(lang, {}) or {}
    out: list[str] = []
    for k, shot in enumerate(storyboard.get("shots", []) or []):
        off = shot_offsets[k] if (shot_offsets and k < len(shot_offsets)) else 0.0
        for layer in shot.get("layers", []) or []:
            key = layer.get("copy_key") or layer.get("role")
            text = copy.get(key, "")
            if not text:
                continue
            bbox = layer.get("bbox", {}) or {}
            t_in = round(max(0.0, float(layer.get("in", 0)) - off), 3)
            t_out = round(max(t_in, float(layer.get("out", 0)) - off), 3)
            anim = str(layer.get("anim") or "")
            out.append(
                # expansion=none: '%'·'{'·'}'를 리터럴로(금리 "3.5%" 등 깨짐·치환 주입 방지)
                "drawtext=" + _fontfile_opt(font_path) + _caption_deco(layer.get("role"))
                + "expansion=none:"
                + f"text='{escape_drawtext(str(text))}'"
                + f":fontsize={int(layer.get('font_px', 48))}"
                + f":fontcolor={_ff_color(layer.get('color', '#FFFFFF'))}"
                + f":x={int(bbox.get('x', 0))}" + _y_part(int(bbox.get("y", 0)), t_in, anim)
                + f":alpha='{_alpha_expr(t_in, t_out)}'"
                + f":enable='between(t,{t_in},{t_out})'"
            )
    return out


@dataclass
class Segment:
    """샷 1개의 렌더 소스. kind: 'video'|'image'|'color'. color는 kind=='color'일 때만."""
    kind: str
    path: str | None
    dur: float
    color: str | None = None


# ── 비주얼 시네마틱 토큰 ───────────────────────────────────────────────
# 정지/단색 세그먼트는 zoompan으로 느린 줌(켄번스)을 줘 "정지 슬라이드" 느낌을 없애고,
# 모든 세그먼트에 동일 컬러그레이드를 입혀 광고 룩(대비·채도·비네팅·샤픈)을 통일한다.
# 실 footage(video)는 이미 카메라 무빙이 있으므로 줌은 생략(이중 무빙·떨림 방지).
_GRADE = ("eq=contrast=1.06:saturation=1.12:gamma=0.985",
          "vignette=PI/6",
          "unsharp=5:5:0.4")
_ZOOM_MAX = 1.12
_ZOOM_RATE = 0.0009


def _segment_chain(i: int, seg: "Segment", *, w: int, h: int, fps: int) -> str:
    """세그먼트 1개 → 정규화+켄번스+그레이드 필터 체인 문자열([i:v]…[vi]).

    모든 입력을 동일 해상도·SAR·fps로 정규화 후 길이 고정(trim) → concat 정합.
    fps 통일 누락 시 image2(기본 25fps)와 lavfi/video가 섞여 concat 타임스탬프 깨짐.
    """
    chain = [f"scale={w}:{h}:force_original_aspect_ratio=increase",
             f"crop={w}:{h}", "setsar=1", f"fps={fps}"]
    if seg.kind in ("image", "color"):
        frames = max(1, int(round(seg.dur * fps)))
        # zoompan: 중심 고정 슬로줌. z·x·y 식은 작은따옴표로 콤마 보호.
        chain.append(
            f"zoompan=z='min(zoom+{_ZOOM_RATE},{_ZOOM_MAX})':d={frames}:s={w}x{h}:fps={fps}"
            ":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'")
    chain.extend(_GRADE)
    chain.append(f"trim=duration={seg.dur}")
    chain.append("setpts=PTS-STARTPTS")
    return f"[{i}:v]" + ",".join(chain) + f"[v{i}]"


# ── 샷 전환(크로스페이드) ──────────────────────────────────────────────
# 하드컷(슬라이드쇼)을 시네마틱 크로스페이드로. 콘티의 샷별 transition_in/out을 존중하되
# 'cut'만 하드컷, 그 외(또는 미지정)는 xfade(기본 dissolve='fade'). 안전 화이트리스트 외
# 이름은 'fade'로 정규화(필터 파싱 에러 방지).
_XFADE_DUR = 0.6                     # 크로스페이드 길이(초)
_XFADE_SAFE = {"fade", "fadeblack", "fadewhite", "dissolve",
               "smoothleft", "smoothright", "smoothup", "smoothdown",
               "wipeleft", "wiperight", "wipeup", "wipedown",
               "slideleft", "slideright", "circleopen", "radial"}
_CUT_ALIASES = {"cut", "none", "hard", "hardcut", "", "0"}


def _xfade_name(raw: str) -> str:
    """xfade transition 이름 정규화 — 'crossfade'/'dissolve'류는 'fade', 미지원은 'fade'."""
    raw = (raw or "").strip().lower()
    if raw in ("crossfade", "crossdissolve", "cross"):
        return "fade"
    return raw if raw in _XFADE_SAFE else "fade"


def _joint_transition(left: dict, right: dict) -> str:
    """조인트 전환 — right.transition_in 우선, 없으면 left.transition_out, 기본 'fade'.

    'cut' 류면 'cut'(하드컷), 그 외엔 정규화된 xfade 이름.
    """
    raw = (right.get("transition_in") or left.get("transition_out") or "fade")
    raw = str(raw).strip().lower()
    return "cut" if raw in _CUT_ALIASES else _xfade_name(raw)


def plan_transitions(storyboard: dict, segments: list["Segment"],
                     *, dur: float = _XFADE_DUR) -> dict:
    """샷 전환 계획 — 조인트 전환 종류·클램프된 D·샷별 시간오프셋·압축 총길이.

    D는 가장 짧은 세그먼트의 절반 이하로 클램프(xfade offset 음수 방지).
    shot_offset[k] = D * (k 이전 페이드 조인트 수) → drawtext 재매핑·xfade offset 공통 기준.
    """
    shots = storyboard.get("shots", []) or []
    n = len(segments)
    joints = [
        _joint_transition(shots[k] if k < len(shots) else {},
                          shots[k + 1] if k + 1 < len(shots) else {})
        for k in range(max(0, n - 1))
    ]
    min_dur = min((s.dur for s in segments), default=dur * 2)
    D = round(max(0.1, min(dur, min_dur * 0.5)), 3)
    shot_offset = [0.0] * n
    cum = 0.0
    for k in range(1, n):
        if joints[k - 1] != "cut":
            cum += D
        shot_offset[k] = round(cum, 3)
    total = round(sum(s.dur for s in segments) - cum, 3)
    return {"joints": joints, "dur": D, "shot_offset": shot_offset, "total": total}


def build_filter_complex(segments: list["Segment"], drawtext: list[str], *,
                         w: int, h: int, fps: int,
                         joints: list[str] | None = None,
                         xfade_dur: float = _XFADE_DUR) -> str:
    """세그먼트 정규화/켄번스/그레이드 → 전환(xfade/cut) pairwise 합성[base] → drawtext → [vout].

    joints[k]='cut'이면 하드컷(concat n=2), 그 외엔 xfade(누적 길이 기준 offset). joints=None은
    전부 'fade'로 간주. xfade_dur은 plan_transitions가 클램프한 D를 그대로 받는다(재클램프 안 함).
    """
    parts: list[str] = []
    for i, seg in enumerate(segments):
        parts.append(_segment_chain(i, seg, w=w, h=h, fps=fps))
    n = len(segments)
    if joints is None:
        joints = ["fade"] * max(0, n - 1)
    D = xfade_dur
    if n == 0:
        return ""
    if n == 1:
        parts.append("[v0]null[base]")
    else:
        acc, acc_len = "v0", segments[0].dur
        for k in range(1, n):
            nxt = "base" if k == n - 1 else f"x{k}"
            jt = joints[k - 1] if k - 1 < len(joints) else "fade"
            if jt == "cut":
                parts.append(f"[{acc}][v{k}]concat=n=2:v=1:a=0[{nxt}]")
                acc_len += segments[k].dur
            else:
                off = max(0.0, acc_len - D)
                parts.append(f"[{acc}][v{k}]xfade=transition={jt}:"
                             f"duration={D}:offset={off:.3f}[{nxt}]")
                acc_len += segments[k].dur - D
            acc = nxt
    if drawtext:
        cur = "base"
        for j, d in enumerate(drawtext):
            nxt = "vout" if j == len(drawtext) - 1 else f"t{j}"
            parts.append(f"[{cur}]{d}[{nxt}]")
            cur = nxt
    else:
        parts.append("[base]null[vout]")
    return ";".join(parts)


def _music_filter(music_idx: int, total_dur: float) -> str:
    """음악 베드 오디오 체인 — 라우드니스 정규화 + 인/아웃 페이드(클립 끝 기준).

    loudnorm으로 베드를 광고 수준(-18 LUFS)으로 맞추고, 시작 1.2s 페이드인 +
    영상 끝 1.5s 전부터 페이드아웃 → 하드 컷오프(-shortest) 클릭/툭 끊김 방지.
    """
    fade_out_st = max(0.0, total_dur - 1.5)
    return (f"[{music_idx}:a]loudnorm=I=-18:TP=-1.5:LRA=11,"
            f"afade=t=in:st=0:d=1.2,"
            f"afade=t=out:st={fade_out_st:.2f}:d=1.5[aout]")


def build_ffmpeg_command(segments: list["Segment"], drawtext: list[str], *,
                         out_path: str, w: int, h: int, fps: int,
                         music_path: str | None,
                         joints: list[str] | None = None,
                         xfade_dur: float = _XFADE_DUR,
                         total: float | None = None) -> list[str]:
    """단일 ffmpeg argv(셸 없음). image=loop, color=lavfi, video=직접 입력. 음악=stream_loop+map.

    joints/xfade_dur은 전환 합성에, total(크로스페이드로 압축된 총길이)은 음악 페이드아웃
    타이밍에 쓰인다. total 미지정 시 concat 가정(=세그먼트 길이 합).
    인코딩은 광고 배포 품질로 튜닝: x264 crf18·preset slow·high profile +
    faststart(웹 스트리밍 시 moov atom 선두 배치로 즉시 재생).
    """
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
    fc = build_filter_complex(segments, drawtext, w=w, h=h, fps=fps,
                              joints=joints, xfade_dur=xfade_dur)
    if music_idx is not None:
        tot = total if total is not None else sum(max(0.0, seg.dur) for seg in segments)
        fc += ";" + _music_filter(music_idx, tot)
    argv += ["-filter_complex", fc]
    argv += ["-map", "[vout]"]
    if music_idx is not None:
        argv += ["-map", "[aout]", "-c:a", "aac", "-b:a", "160k", "-shortest"]
    argv += ["-r", str(fps), "-c:v", "libx264", "-preset", "slow", "-crf", "18",
             "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
             "-movflags", "+faststart", out_path]
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


# Windows 로컬(dev/검증) CJK 폰트 폴백 — 배포(Linux)는 위 후보가 먼저 잡힌다.
# drawtext fontfile은 작은따옴표로 감싸 콜론(C:)이 보호되므로 슬래시만 통일하면 됨.
_WIN_FONT_CANDIDATES = (
    "C:/Windows/Fonts/malgun.ttf",      # 맑은 고딕(한글)
    "C:/Windows/Fonts/malgunsl.ttf",
    "C:/Windows/Fonts/gulim.ttc",
    "C:/Windows/Fonts/batang.ttc",
)


def _norm_font(p: str) -> str:
    """drawtext fontfile용 경로 정규화 — 역슬래시→슬래시(Windows 경로 escape 회피)."""
    return str(p).replace("\\", "/")


def _resolve_font() -> str | None:
    p = os.environ.get("MARKER_CJK_FONT")
    if p and Path(p).exists():
        return _norm_font(p)
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
                return _norm_font(hits[0])
    for c in _WIN_FONT_CANDIDATES:        # 로컬 Windows 검증 폴백(배포엔 영향 없음)
        if Path(c).exists():
            return c
    return None


def _resolve_music() -> str | None:
    """backend/assets/music/bed.* 음악 베드. 동봉 CC0 패드(README 참조). 없으면 무음."""
    base = Path(__file__).resolve().parents[3] / "assets" / "music"
    for ext in ("m4a", "mp3", "wav", "aac", "ogg"):
        f = base / f"bed.{ext}"
        if f.exists():
            return str(f)
    return None


# 종횡비 → 캔버스 해상도(짝수·1080 기준). 콘티 aspect 토큰을 실제 렌더 캔버스로 반영.
_ASPECT_DIMS = {
    "9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080),
    "4:5": (1080, 1350), "3:4": (1080, 1440), "2:3": (1080, 1620),
}


def _dims_for_aspect(aspect: str | None) -> tuple[int, int]:
    """aspect 문자열 → (w,h). 미지정/미지원은 9:16 세로(기존 기본)로 폴백."""
    return _ASPECT_DIMS.get((aspect or "9:16").strip(), (1080, 1920))


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
    w, h = _dims_for_aspect(storyboard.get("aspect"))
    fps = int(storyboard.get("fps", 30) or 30)
    ffmpeg_bin = _resolve_ffmpeg(ffmpeg)

    data = STUB_MP4
    render_error: str | None = None
    if ffmpeg_bin:
        with tempfile.TemporaryDirectory() as td:
            segs = _build_segments(store, run_id, storyboard, td, w=w, h=h)
            if segs:
                plan = plan_transitions(storyboard, segs)
                dt = build_drawtext_filters(storyboard, lang, font_path=_resolve_font(),
                                            shot_offsets=plan["shot_offset"])
                local_out = str(Path(td) / "final.mp4")
                argv = build_ffmpeg_command(
                    segs, dt, out_path=local_out, w=w, h=h, fps=fps,
                    music_path=_resolve_music(), joints=plan["joints"],
                    xfade_dur=plan["dur"], total=plan["total"])
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
