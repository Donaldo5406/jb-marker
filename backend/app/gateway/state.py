"""스튜디오 _state.json 공용 I/O — 경로 규약·source/mime·version 단일화 (T1-P1, spec §7-4).

상태 '내용'(기본값·정규화)은 각 하네스 도메인 책임으로 남긴다. 여기는 위치와
직렬화 규약만 책임진다. 기존 라이브 run(버전 無)은 로드 시 그대로 통과하고
다음 저장에서 version이 백필된다(가산적 — 행동 보존 D6).
"""
from __future__ import annotations

import json
from typing import Callable

STATE_VERSION = 1


def state_path(run_id: str, studio: str) -> str:
    return f"/{run_id}/{studio}/_state.json"


def load_state(store, run_id: str, studio: str, *,
               default_factory: Callable[[], dict]) -> dict:
    n = store.get(state_path(run_id, studio))
    if n and n.content_text:
        return json.loads(n.content_text)
    return default_factory()


def save_state(store, run_id: str, studio: str, state: dict) -> None:
    state.setdefault("version", STATE_VERSION)
    store.put(state_path(run_id, studio), json.dumps(state, ensure_ascii=False),
              source="marker", mime="application/json")
