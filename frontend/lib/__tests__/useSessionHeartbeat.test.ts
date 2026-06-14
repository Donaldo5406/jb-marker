import { renderHook } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useSessionHeartbeat } from "../useSessionHeartbeat";

describe("useSessionHeartbeat", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("마운트 즉시 1회 + interval마다 onTick 호출", () => {
    const onTick = vi.fn();
    renderHook(() => useSessionHeartbeat("r1", "design", onTick, { intervalMs: 1000 }));
    expect(onTick).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(2000);
    expect(onTick).toHaveBeenCalledTimes(3);
    expect(onTick).toHaveBeenLastCalledWith("design");
  });

  it("runId가 null이면 호출하지 않는다", () => {
    const onTick = vi.fn();
    renderHook(() => useSessionHeartbeat(null, "design", onTick, { intervalMs: 1000 }));
    vi.advanceTimersByTime(3000);
    expect(onTick).not.toHaveBeenCalled();
  });

  it("document.hidden이면 tick을 건너뛴다", () => {
    const onTick = vi.fn();
    const spy = vi.spyOn(document, "hidden", "get").mockReturnValue(true);
    renderHook(() => useSessionHeartbeat("r1", "design", onTick, { intervalMs: 1000 }));
    vi.advanceTimersByTime(2000);
    expect(onTick).not.toHaveBeenCalled();
    spy.mockRestore();
  });
});
