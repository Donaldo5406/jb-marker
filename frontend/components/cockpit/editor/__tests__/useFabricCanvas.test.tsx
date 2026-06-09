import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import * as React from "react";

const add = vi.fn();
const clear = vi.fn();
const renderAll = vi.fn();
const dispose = vi.fn();
vi.mock("fabric", () => ({
  Canvas: vi.fn().mockImplementation(() => ({
    add, clear, renderAll, dispose,
    sendObjectToBack: vi.fn(),
    toObject: vi.fn(() => ({ version: "6.0.0", objects: [] })),
    on: vi.fn(), off: vi.fn(),
  })),
  Textbox: vi.fn().mockImplementation((t: string) => ({ kind: "textbox", text: t })),
  FabricImage: { fromURL: vi.fn(async () => ({ kind: "image", set: vi.fn(), scaleToWidth: vi.fn() })) },
  FabricObject: { ownDefaults: {} },
}));
vi.mock("@/lib/fabricDefaults", () => ({}));
vi.mock("@/lib/api", () => ({ authedFetch: vi.fn(async () => ({ ok: false })) }));

import { useFabricCanvas } from "../useFabricCanvas";

beforeEach(() => { add.mockClear(); clear.mockClear(); });

describe("useFabricCanvas", () => {
  it("scene의 textbox를 동기 add 한다", () => {
    const elRef = { current: document.createElement("canvas") } as React.RefObject<HTMLCanvasElement>;
    // scene은 안정적(메모이즈된) 참조여야 한다 — 프로덕션은 useMemo([content])로 보장.
    // 매 렌더 새 객체를 넘기면 로드 완료(loadVersion) 리렌더가 로드 effect를 재실행시켜 루프가 된다.
    const scene = { version: "6.0.0", objects: [{ type: "textbox", text: "안녕", left: 10, top: 10, width: 100 }], width: 1080, height: 1080 };
    renderHook(() => useFabricCanvas(elRef, scene));
    expect(clear).toHaveBeenCalled();
    expect(add).toHaveBeenCalledTimes(1);  // textbox 1개
  });
});
