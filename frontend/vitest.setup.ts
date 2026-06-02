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

// jsdom은 matchMedia도 제공하지 않는다. motion(framer)의 useReducedMotion 등이
// 마운트 시 window.matchMedia를 호출하므로, 항상 "비-reduce"를 답하는 stub을 둔다.
if (typeof globalThis.matchMedia === "undefined") {
  globalThis.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof globalThis.matchMedia;
}
