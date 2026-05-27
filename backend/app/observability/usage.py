"""Usage logger — VFS `/{runId}/usage/log.jsonl`에 한 줄 append + summary.

각 LLM/이미지 호출 직후 호출자가 `record_usage(...)` 한 번 호출.
스트림 형식이므로 동시성 안전(append-only).
"""
from __future__ import annotations

import json
import time
from typing import Any

from . import pricing


def _log_path(run_id: str) -> str:
    return f"/{run_id}/usage/log.jsonl"


def record_usage(
    store,
    *,
    run_id: str,
    step: str,
    model: str,
    kind: str = "text",
    usage: dict | None = None,
    images: int = 0,
    meta: dict[str, Any] | None = None,
) -> dict:
    """한 LLM/이미지 호출의 사용량을 VFS 로그에 append.

    - step: "brainstorming" | "design" | "review" | "deploy" | "advisor" | "gateway" 등
    - kind: "text" | "vision" | "image"
    - usage: {"input_tokens", "output_tokens"} 또는 None(알 수 없음)
    - images: kind="image"일 때 생성 장수
    - meta: 추가 메타데이터 (turn_id, package_id 등)

    반환: 기록한 entry dict.
    """
    in_tok = int((usage or {}).get("input_tokens", 0) or 0)
    out_tok = int((usage or {}).get("output_tokens", 0) or 0)
    if kind == "image":
        cost = pricing.image_cost_usd(model, images)
    else:
        cost = pricing.text_cost_usd(model, in_tok, out_tok)

    entry = {
        "ts": time.time(),
        "step": step,
        "kind": kind,
        "model": model,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "images": int(images),
        "cost_usd": round(cost, 6),
        "known_model": pricing.is_known(model),
        "meta": meta or {},
    }

    path = _log_path(run_id)
    existing = store.get_text(path) or ""
    store.put_text(path, existing + json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_log(store, *, run_id: str) -> list[dict]:
    raw = store.get_text(_log_path(run_id))
    if not raw:
        return []
    out: list[dict] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def summarize(store, *, run_id: str) -> dict:
    """로그를 step·model별로 집계.

    반환 구조:
    {
      "total": {"input_tokens", "output_tokens", "images", "cost_usd", "calls"},
      "by_step": {step: {"input_tokens", ..., "by_model": {model: {...}}}},
      "entries": [...],   # raw log
    }
    """
    entries = read_log(store, run_id=run_id)
    total = {"input_tokens": 0, "output_tokens": 0, "images": 0, "cost_usd": 0.0, "calls": 0}
    by_step: dict[str, dict] = {}

    for e in entries:
        total["input_tokens"] += e["input_tokens"]
        total["output_tokens"] += e["output_tokens"]
        total["images"] += e["images"]
        total["cost_usd"] += e["cost_usd"]
        total["calls"] += 1

        step = e["step"]
        s = by_step.setdefault(step, {
            "input_tokens": 0, "output_tokens": 0, "images": 0,
            "cost_usd": 0.0, "calls": 0, "by_model": {},
        })
        s["input_tokens"] += e["input_tokens"]
        s["output_tokens"] += e["output_tokens"]
        s["images"] += e["images"]
        s["cost_usd"] += e["cost_usd"]
        s["calls"] += 1

        m = e["model"]
        mm = s["by_model"].setdefault(m, {
            "input_tokens": 0, "output_tokens": 0, "images": 0,
            "cost_usd": 0.0, "calls": 0,
        })
        mm["input_tokens"] += e["input_tokens"]
        mm["output_tokens"] += e["output_tokens"]
        mm["images"] += e["images"]
        mm["cost_usd"] += e["cost_usd"]
        mm["calls"] += 1

    total["cost_usd"] = round(total["cost_usd"], 6)
    for s in by_step.values():
        s["cost_usd"] = round(s["cost_usd"], 6)
        for mm in s["by_model"].values():
            mm["cost_usd"] = round(mm["cost_usd"], 6)

    return {"total": total, "by_step": by_step, "entries": entries}
