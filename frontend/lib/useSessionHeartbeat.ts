"use client";
import { useEffect, useRef } from "react";

/** runId+studio 세션을 주기적으로 heartbeat 폴링(~60s). document.hidden이면 건너뛰고,
 *  탭이 다시 보이면 즉시 1회. runId 없으면 no-op. useRunSocket의 poll(4s 트리 재조회)과 별개. */
export function useSessionHeartbeat(
  runId: string | null,
  studio: string,
  onTick: (studio: string) => void,
  opts: { intervalMs?: number } = {},
) {
  const onTickRef = useRef(onTick);
  onTickRef.current = onTick;
  const intervalMs = opts.intervalMs ?? 60000;

  useEffect(() => {
    if (!runId) return;
    const tick = () => {
      if (typeof document !== "undefined" && document.hidden) return;
      onTickRef.current(studio);
    };
    tick();   // 진입 즉시 1회
    const timer = setInterval(tick, intervalMs);
    const onVis = () => { if (!document.hidden) tick(); };
    if (typeof document !== "undefined") document.addEventListener("visibilitychange", onVis);
    return () => {
      clearInterval(timer);
      if (typeof document !== "undefined") document.removeEventListener("visibilitychange", onVis);
    };
  }, [runId, studio, intervalMs]);
}
