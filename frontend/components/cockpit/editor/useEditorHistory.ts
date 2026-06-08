import { useCallback, useRef, useState } from "react";

/** 문자열 스냅샷(.scene JSON) 기반 undo/redo 스택.
 *  push: 현재 위치 이후(redo 분기)를 잘라내고 스냅샷 추가.
 *  undo: 직전 스냅샷 반환(없으면 null). redo: 다음 스냅샷 반환(없으면 null).
 *  캔버스에 독립적 — 호출부가 반환 스냅샷을 캔버스에 로드한다. */
export function useEditorHistory() {
  const stackRef = useRef<string[]>([]);
  const posRef = useRef(-1);
  const [, force] = useState(0);
  const rerender = () => force((n) => n + 1);

  const push = useCallback((snapshot: string) => {
    stackRef.current = stackRef.current.slice(0, posRef.current + 1);
    stackRef.current.push(snapshot);
    posRef.current = stackRef.current.length - 1;
    rerender();
  }, []);

  const undo = useCallback((): string | null => {
    if (posRef.current <= 0) return null;
    posRef.current -= 1;
    rerender();
    return stackRef.current[posRef.current];
  }, []);

  const redo = useCallback((): string | null => {
    if (posRef.current >= stackRef.current.length - 1) return null;
    posRef.current += 1;
    rerender();
    return stackRef.current[posRef.current];
  }, []);

  const reset = useCallback((snapshot?: string) => {
    stackRef.current = snapshot != null ? [snapshot] : [];
    posRef.current = snapshot != null ? 0 : -1;
    rerender();
  }, []);

  return {
    push, undo, redo, reset,
    canUndo: posRef.current > 0,
    canRedo: posRef.current < stackRef.current.length - 1,
  };
}
