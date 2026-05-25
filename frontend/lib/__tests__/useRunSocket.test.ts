import { describe, it, expect, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useRunSocket } from "../useRunSocket";

class FakeWS {
  static last: FakeWS | null = null;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
  constructor(public url: string) { FakeWS.last = this; }
}

describe("useRunSocket", () => {
  it("연결 후 메시지를 onEvent로 전달", () => {
    vi.stubGlobal("WebSocket", FakeWS as unknown as typeof WebSocket);
    const onEvent = vi.fn();
    renderHook(() => useRunSocket("run1", onEvent));
    FakeWS.last!.onopen?.();
    FakeWS.last!.onmessage?.({ data: JSON.stringify({ type: "artifact", path: "/run1/brainstorming/passthrough.md" }) });
    expect(onEvent).toHaveBeenCalledWith({ type: "artifact", path: "/run1/brainstorming/passthrough.md" });
  });

  it("runId가 null이면 연결하지 않음", () => {
    FakeWS.last = null;
    vi.stubGlobal("WebSocket", FakeWS as unknown as typeof WebSocket);
    renderHook(() => useRunSocket(null, vi.fn()));
    expect(FakeWS.last).toBeNull();
  });
});
