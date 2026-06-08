import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useEditorHistory } from "../useEditorHistory";

describe("useEditorHistory", () => {
  it("초기엔 undo/redo 불가", () => {
    const { result } = renderHook(() => useEditorHistory());
    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(false);
  });

  it("push 후 undo는 직전 스냅샷, redo는 복구", () => {
    const { result } = renderHook(() => useEditorHistory());
    act(() => result.current.push("A"));
    act(() => result.current.push("B"));
    expect(result.current.canUndo).toBe(true);
    let undone: string | null = null;
    act(() => { undone = result.current.undo(); });
    expect(undone).toBe("A");              // 현재 B → 직전 A
    expect(result.current.canRedo).toBe(true);
    let redone: string | null = null;
    act(() => { redone = result.current.redo(); });
    expect(redone).toBe("B");
  });

  it("undo 이후 새 push는 redo 분기를 폐기", () => {
    const { result } = renderHook(() => useEditorHistory());
    act(() => result.current.push("A"));
    act(() => result.current.push("B"));
    act(() => { result.current.undo(); });   // 현재 A
    act(() => result.current.push("C"));     // redo(B) 폐기
    expect(result.current.canRedo).toBe(false);
    let undone: string | null = null;
    act(() => { undone = result.current.undo(); });
    expect(undone).toBe("A");
  });

  it("스냅샷 1개뿐이면 undo는 null", () => {
    const { result } = renderHook(() => useEditorHistory());
    act(() => result.current.push("A"));
    expect(result.current.canUndo).toBe(false);
    let r: string | null = "x";
    act(() => { r = result.current.undo(); });
    expect(r).toBeNull();
  });
});
