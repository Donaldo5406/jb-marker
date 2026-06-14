"""Video 렌더 서비스 — 확정 storyboard → ffmpeg → review/_render/final.mp4 (spec §5).

순수 빌더(spec→ffmpeg argv)와 오케스트레이터(render_video)를 분리한다. 모든 빌더는
ffmpeg 바이너리 없이 결정론적으로 테스트된다. 렌더 전 고지 ≥3초를 evaluate_timing으로
서버 재검증(프론트와 이중) — 위반 시 ComplianceError(→ 라우터에서 422).
"""
from __future__ import annotations

import json

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
