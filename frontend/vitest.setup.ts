import "@testing-library/jest-dom/vitest";

// jsdom은 ResizeObserver를 제공하지 않는다. react-resizable-panels 등
// 레이아웃 측정 컴포넌트가 마운트 시 사용하므로 최소 stub을 전역 등록한다.
if (typeof globalThis.ResizeObserver === "undefined") {
  class ResizeObserverStub {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  }
  globalThis.ResizeObserver =
    ResizeObserverStub as unknown as typeof ResizeObserver;
}
