"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  parseStoryboard, storyboardDuration, type Storyboard,
} from "@/lib/video/storyboard";

export type Selection = { shotId: string; layerIdx: number } | null;

export type VideoTimeline = {
  sb: Storyboard | null;
  duration: number;
  time: number;
  playing: boolean;
  sel: Selection;
  dirty: boolean;
  seek: (t: number) => void;
  setPlaying: (p: boolean) => void;
  selectLayer: (shotId: string, layerIdx: number) => void;
  clearSelection: () => void;
  editCopy: (lang: string, key: string, value: string) => void;
  editLayerTiming: (shotId: string, layerIdx: number, field: "in" | "out", value: number) => void;
  serialized: () => string;
};

/** storyboard 편집 상태 훅. content(JSON)을 파싱해 보유, 편집은 불변 갱신 + dirty 마킹.
 *  재생은 rAF로 time을 진행(테스트는 재생 미사용). */
export function useVideoTimeline(content: string): VideoTimeline {
  const [sb, setSb] = useState<Storyboard | null>(() => parseStoryboard(content));
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [sel, setSel] = useState<Selection>(null);
  const [dirty, setDirty] = useState(false);

  // content(새 storyboard 로드) 변경 시 재파싱 + 편집상태 리셋.
  useEffect(() => {
    setSb(parseStoryboard(content));
    setDirty(false);
    setTime(0);
    setSel(null);
    setPlaying(false);
  }, [content]);

  const duration = sb ? storyboardDuration(sb) : 0;

  const seek = useCallback(
    (t: number) => setTime(Math.max(0, Math.min(duration, t))),
    [duration],
  );

  // 재생: rAF로 time 진행, duration 도달 시 정지.
  const lastRef = useRef(0);
  useEffect(() => {
    if (!playing || duration <= 0) return;
    let raf = 0;
    lastRef.current = 0;
    const tick = (ts: number) => {
      if (!lastRef.current) lastRef.current = ts;
      const dt = (ts - lastRef.current) / 1000;
      lastRef.current = ts;
      setTime((t) => {
        const n = t + dt;
        if (n >= duration) return duration;
        return n;
      });
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing, duration]);

  // duration 끝에 닿으면 자동 정지.
  useEffect(() => {
    if (playing && duration > 0 && time >= duration) setPlaying(false);
  }, [playing, time, duration]);

  const selectLayer = useCallback((shotId: string, layerIdx: number) => {
    setSel({ shotId, layerIdx });
  }, []);
  const clearSelection = useCallback(() => setSel(null), []);

  const editCopy = useCallback((lang: string, key: string, value: string) => {
    setSb((prev) => {
      if (!prev) return prev;
      const copy = { ...(prev.copy ?? {}) };
      copy[lang] = { ...(copy[lang] ?? {}), [key]: value };
      return { ...prev, copy };
    });
    setDirty(true);
  }, []);

  const editLayerTiming = useCallback(
    (shotId: string, layerIdx: number, field: "in" | "out", value: number) => {
      setSb((prev) => {
        if (!prev) return prev;
        const shots = (prev.shots ?? []).map((s) => {
          if (s.id !== shotId) return s;
          const layers = (s.layers ?? []).map((l, i) =>
            i === layerIdx ? { ...l, [field]: value } : l,
          );
          return { ...s, layers };
        });
        return { ...prev, shots };
      });
      setDirty(true);
    },
    [],
  );

  const serialized = useCallback(() => JSON.stringify(sb ?? {}), [sb]);

  return {
    sb, duration, time, playing, sel, dirty,
    seek, setPlaying, selectLayer, clearSelection, editCopy, editLayerTiming, serialized,
  };
}
