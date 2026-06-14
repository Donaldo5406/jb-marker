import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useVideoTimeline } from "../useVideoTimeline";

const SB = {
  duration_sec: 15, aspect: "9:16",
  shots: [
    { id: "s1", start: 0, end: 5, layers: [
      { role: "headline", in: 0.5, out: 4 },
      { role: "disclosure", in: 1, out: 4 },
    ] },
  ],
  copy: { ko: { headline: "안녕", disclosure: "보호" }, en: {} },
};
const content = JSON.stringify(SB);

describe("useVideoTimeline", () => {
  it("content를 파싱하고 duration·dirty 초기값", () => {
    const { result } = renderHook(() => useVideoTimeline(content));
    expect(result.current.sb?.shots?.length).toBe(1);
    expect(result.current.duration).toBe(15);
    expect(result.current.dirty).toBe(false);
    expect(result.current.time).toBe(0);
  });

  it("selectLayer로 선택 상태 갱신", () => {
    const { result } = renderHook(() => useVideoTimeline(content));
    act(() => result.current.selectLayer("s1", 0));
    expect(result.current.sel).toEqual({ shotId: "s1", layerIdx: 0 });
  });

  it("editCopy로 copy 갱신 + dirty", () => {
    const { result } = renderHook(() => useVideoTimeline(content));
    act(() => result.current.editCopy("ko", "headline", "수정됨"));
    expect(result.current.sb?.copy?.ko?.headline).toBe("수정됨");
    expect(result.current.dirty).toBe(true);
  });

  it("editLayerTiming으로 in/out 갱신 + dirty", () => {
    const { result } = renderHook(() => useVideoTimeline(content));
    act(() => result.current.editLayerTiming("s1", 1, "out", 4.5));
    const disc = result.current.sb?.shots?.[0]?.layers?.[1];
    expect(disc?.out).toBe(4.5);
    expect(result.current.dirty).toBe(true);
  });

  it("seek로 time 갱신(0~duration 클램프)", () => {
    const { result } = renderHook(() => useVideoTimeline(content));
    act(() => result.current.seek(99));
    expect(result.current.time).toBe(15);
    act(() => result.current.seek(-1));
    expect(result.current.time).toBe(0);
  });

  it("content 변경 시 재파싱 + dirty 리셋", () => {
    const { result, rerender } = renderHook(({ c }) => useVideoTimeline(c), {
      initialProps: { c: content },
    });
    act(() => result.current.editCopy("ko", "headline", "X"));
    expect(result.current.dirty).toBe(true);
    const SB2 = { ...SB, duration_sec: 20 };
    rerender({ c: JSON.stringify(SB2) });
    expect(result.current.duration).toBe(20);
    expect(result.current.dirty).toBe(false);
  });

  it("serialized로 현재 sb를 JSON 직렬화", () => {
    const { result } = renderHook(() => useVideoTimeline(content));
    act(() => result.current.editCopy("ko", "headline", "Z"));
    expect(JSON.parse(result.current.serialized()).copy.ko.headline).toBe("Z");
  });
});
