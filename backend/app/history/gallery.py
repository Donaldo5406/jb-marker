"""History 갤러리 집계 — VFS 노드를 스튜디오 단계별 섹션으로 그룹핑.

정렬·의미 규칙의 단일 소스(spec §4). 순수 함수: I/O 없음, 테스트 용이.
"""
from __future__ import annotations

from ..vfs.types import Manifest, VfsNode

STUDIO_ORDER = ["brainstorming", "design", "review", "deploy"]
STUDIO_LABELS = {
    "brainstorming": "기획", "design": "디자인", "review": "검토", "deploy": "배포",
}
# 섹션 내 그룹 노출 순서 — 시각 산출물 먼저.
KIND_ORDER = ["image", "scene", "video", "document", "data"]
_MEDIA_KINDS = {"image", "scene", "video"}


def _segments(path: str) -> list[str]:
    return [seg for seg in path.split("/") if seg]


def _is_hidden(path: str) -> bool:
    """경로의 임의 세그먼트가 '_'로 시작하면 숨김(_state.json, _render/ 등)."""
    return any(seg.startswith("_") for seg in _segments(path))


def _studio_of(path: str) -> str | None:
    """/{run}/<studio>/... 의 2번째 세그먼트. 파일 깊이 미달이면 None(루트 manifest.json 등)."""
    segs = _segments(path)
    return segs[1] if len(segs) >= 3 else None


def _kind_of(path: str, mime: str | None) -> str:
    segs = _segments(path)
    name = segs[-1] if segs else ""
    if name.endswith(".scene"):
        return "scene"
    m = (mime or "").lower()
    if m.startswith("image/"):
        return "image"
    if m.startswith("video/"):
        return "video"
    if name.endswith((".md", ".json", ".txt")) or m in (
        "text/markdown", "application/json", "text/plain",
    ):
        return "document"
    return "data"


def _item(node: VfsNode) -> dict:
    segs = _segments(node.path)
    kind = _kind_of(node.path, node.mime)
    return {
        "path": node.path,
        "name": segs[-1] if segs else node.path,
        "mime": node.mime,
        "source": node.source,
        "is_media": kind in _MEDIA_KINDS,
        "meta": node.meta or {},
    }


def build_gallery(manifest: Manifest, nodes: list[VfsNode]) -> dict:
    run_id = manifest.run_id
    # 스튜디오별 노드 수집(숨김·비-스튜디오·디렉터리 제외).
    buckets: dict[str, list[VfsNode]] = {s: [] for s in STUDIO_ORDER}
    has_tokens = False
    for n in nodes:
        if n.kind == "dir":
            continue
        if _is_hidden(n.path):
            continue
        if n.path.endswith("/design/design-system/tokens.json"):
            has_tokens = True
        studio = _studio_of(n.path)
        if studio in buckets:
            buckets[studio].append(n)

    sections = []
    for studio in STUDIO_ORDER:
        items = [_item(n) for n in buckets[studio]]
        # kind별 그룹화 + 그룹 내 path 사전순.
        by_kind: dict[str, list[dict]] = {}
        for it in items:
            by_kind.setdefault(_kind_of(it["path"], it["mime"]), []).append(it)
        groups = []
        for kind in KIND_ORDER:
            if kind in by_kind:
                groups.append({
                    "kind": kind,
                    "items": sorted(by_kind[kind], key=lambda i: i["path"]),
                })
        sections.append({
            "studio": studio,
            "label": STUDIO_LABELS[studio],
            "status": manifest.step_status.get(studio, "none"),
            "has_preview": studio == "design" and has_tokens,
            "groups": groups,
        })

    return {
        "run": {
            "run_id": run_id,
            "title": manifest.title,
            "created_at": manifest.created_at,
            "current_step": manifest.current_step,
            "step_status": manifest.step_status,
            "languages": manifest.languages,
        },
        "sections": sections,
    }
