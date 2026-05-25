"""논리 경로 규약 /{runId}/{studio}/... 파싱·검증 (vfs.md CRUD 규약)."""
from __future__ import annotations

from .types import STUDIOS


def parse_path(path: str) -> tuple[str, str, str]:
    """/{runId}/{studio}/{rest} → (runId, studio, rest)."""
    parts = path.strip("/").split("/", 2)
    if len(parts) < 2:
        raise ValueError(f"경로에 studio 세그먼트가 없음: {path!r}")
    run_id, studio = parts[0], parts[1]
    rest = parts[2] if len(parts) == 3 else ""
    return run_id, studio, rest


def validate_path(path: str) -> None:
    run_id, studio, _ = parse_path(path)
    if not run_id:
        raise ValueError(f"runId 누락: {path!r}")
    if studio not in STUDIOS:
        raise ValueError(f"알 수 없는 studio {studio!r} (허용: {STUDIOS})")
