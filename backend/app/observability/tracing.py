"""Langfuse 트레이싱 + Sentry run 태그 — TrackedProvider 단일 관문에서 호출 (spec 2026-06-12).

설계 불변식:
- 키 부재·SDK 미설치·전송 실패 어느 경우에도 호출자에게 예외를 던지지 않는다(no-op).
- 외부 SDK(langfuse·sentry_sdk) 접점은 이 모듈에만 존재한다.
- trace_id는 run_id 시드의 결정론 해시 → 한 run의 모든 호출이 한 트레이스로 묶이고,
  tag_run의 Sentry 컨텍스트 링크와 항상 일치한다.
"""
from __future__ import annotations

import hashlib
from typing import Any

_client = None          # Langfuse 클라이언트 — 프로세스당 1개
_client_failed = False  # init 실패 시 재시도 방지


def _trace_id(run_id: str) -> str:
    """run_id → 32자 hex trace ID (OTel 형식). record_generation·tag_run 공용."""
    return hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:32]


def _get_client(settings):
    """Langfuse 클라이언트 lazy init. 키 부재/미설치/실패 → None."""
    global _client, _client_failed
    if _client is not None:
        return _client
    if _client_failed:
        return None
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return None
    try:
        from langfuse import Langfuse
        _client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        return _client
    except Exception:
        _client_failed = True
        return None


def record_generation(
    settings,
    *,
    run_id: str,
    step: str,
    model: str,
    kind: str = "text",
    input_payload: Any = None,
    output_text: str | None = None,
    usage: dict | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    """한 LLM/이미지 호출을 Langfuse generation으로 기록. 실패는 조용히 무시."""
    try:
        client = _get_client(settings)
        if client is None:
            return
        metadata: dict[str, Any] = {"kind": kind, "run_id": run_id, **(meta or {})}
        if settings.sentry_issues_url:
            metadata["sentry_search_url"] = (
                f"{settings.sentry_issues_url.rstrip('/')}/?query=run_id%3A{run_id}"
            )
        gen = client.start_generation(
            name=f"{step}/{kind}",
            model=model,
            input=input_payload,
            metadata=metadata,
            trace_context={"trace_id": _trace_id(run_id)},
        )
        usage_details = None
        if usage:
            usage_details = {
                "input": int(usage.get("input_tokens", 0) or 0),
                "output": int(usage.get("output_tokens", 0) or 0),
            }
        gen.update(output=output_text, usage_details=usage_details)
        gen.update_trace(name=f"run:{run_id}", metadata=metadata)
        gen.end()
    except Exception:
        return


def tag_run(run_id: str, settings) -> None:
    """현재 Sentry 스코프에 run_id 태그 + Langfuse trace 링크 컨텍스트. no-op 안전."""
    try:
        if not settings.sentry_dsn:
            return
        import sentry_sdk
        sentry_sdk.set_tag("run_id", run_id)
        if settings.langfuse_project_id:
            url = (f"{settings.langfuse_host.rstrip('/')}/project/"
                   f"{settings.langfuse_project_id}/traces/{_trace_id(run_id)}")
            sentry_sdk.set_context("langfuse", {"trace_url": url})
    except Exception:
        return


def flush() -> None:
    """배치 강제 전송 — 앱 shutdown 훅에서 호출 (HF Spaces 재시작 대비)."""
    try:
        if _client is not None:
            _client.flush()
    except Exception:
        return
