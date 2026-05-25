"use client";
import { useEffect, useRef } from "react";
import { api } from "./api";
import type { AskPayload } from "./api";

export type RunEvent = { type: string; path?: string; ask?: AskPayload };

/** runId의 WS에 연결해 이벤트를 onEvent로 흘린다. 끊기면 지수 백오프 재연결.
 *  WS 실패 시 pollMs 간격 폴백(onPoll 호출)로 트리 갱신을 유도. */
export function useRunSocket(
  runId: string | null,
  onEvent: (e: RunEvent) => void,
  opts: { pollMs?: number } = {},
) {
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!runId) return;
    let closed = false;
    let ws: WebSocket | null = null;
    let retry = 0;
    let pollTimer: ReturnType<typeof setInterval> | null = null;

    const startPoll = () => {
      if (pollTimer || !opts.pollMs) return;
      pollTimer = setInterval(() => onEventRef.current({ type: "poll" }), opts.pollMs);
    };
    const stopPoll = () => { if (pollTimer) { clearInterval(pollTimer); pollTimer = null; } };

    const connect = () => {
      if (closed) return;
      try {
        ws = new WebSocket(api.wsUrl(runId));
      } catch { startPoll(); return; }
      ws.onopen = () => { retry = 0; stopPoll(); };
      ws.onmessage = (ev) => {
        try { onEventRef.current(JSON.parse(ev.data) as RunEvent); } catch { /* ignore */ }
      };
      ws.onclose = () => {
        if (closed) return;
        startPoll();
        retry += 1;
        const delay = Math.min(1000 * 2 ** retry, 15000);
        setTimeout(connect, delay);
      };
      ws.onerror = () => { ws?.close(); };
    };
    connect();

    return () => { closed = true; stopPoll(); ws?.close(); };
  }, [runId, opts.pollMs]);
}
