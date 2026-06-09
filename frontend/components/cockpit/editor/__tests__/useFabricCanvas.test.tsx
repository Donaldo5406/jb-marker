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
  FabricImage: {
    fromURL: vi.fn(async () => ({ kind: "image", set: vi.fn(), scaleToWidth: vi.fn() })),
    fromObject: vi.fn(async (o: any) => ({ kind: "image", ...o, set: vi.fn(), scaleToWidth: vi.fn() })),
  },
  FabricObject: { ownDefaults: {} },
}));
vi.mock("@/lib/fabricDefaults", () => ({}));
vi.mock("@/lib/api", () => ({ authedFetch: vi.fn(async () => ({ ok: false })) }));

import { useFabricCanvas } from "../useFabricCanvas";
import { FabricImage } from "fabric";
import { authedFetch } from "@/lib/api";
import { waitFor } from "@testing-library/react";

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

  it("에디터 저장 이미지(scaleX·filters)는 fromObject로 전체 복원한다 (P3 회귀 가드)", async () => {
    vi.mocked(authedFetch).mockResolvedValue({ ok: true, blob: async () => new Blob() } as any);
    const origCreate = URL.createObjectURL;
    (URL as any).createObjectURL = vi.fn(() => "blob:x");
    (URL as any).revokeObjectURL = vi.fn();
    try {
      const elRef = { current: document.createElement("canvas") } as React.RefObject<HTMLCanvasElement>;
      const scene = { version: "6.0.0", width: 1080, height: 1080, objects: [
        { type: "image", assetPath: "/vfs/r/a.png", scaleX: 0.5, scaleY: 0.5, left: 0, top: 0,
          filters: [{ type: "Brightness", brightness: 0.2 }] },
      ] };
      renderHook(() => useFabricCanvas(elRef, scene));
      await waitFor(() => expect((FabricImage as any).fromObject).toHaveBeenCalled());
      const arg = (FabricImage as any).fromObject.mock.calls[0][0];
      expect(arg.filters).toEqual([{ type: "Brightness", brightness: 0.2 }]);
      expect(arg.src).toBe("blob:x");
    } finally {
      (URL as any).createObjectURL = origCreate;
    }
  });
});
