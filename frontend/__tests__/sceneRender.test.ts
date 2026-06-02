import { describe, it, expect, vi, beforeEach } from "vitest";

// fabric named import을 mock: StaticCanvas(sceneRender) + FabricObject(fabricDefaults가
// v7 origin 복원에 사용). vitest는 정의 안 된 export 접근만으로 throw하므로 둘 다 필요.
vi.mock("fabric", () => ({
  StaticCanvas: vi.fn().mockImplementation(() => ({
    loadFromJSON: vi.fn(() => Promise.resolve()),
    renderAll: vi.fn(),
    toDataURL: vi.fn(() => "data:image/png;base64,AAAA"),
    dispose: vi.fn(),
  })),
  FabricObject: { ownDefaults: {} },
}));

import { renderSceneToPng, uploadRender, renderAndUploadAll } from "../lib/sceneRender";

describe("renderSceneToPng", () => {
  it("dataURL을 반환한다", async () => {
    const url = await renderSceneToPng({ objects: [] });
    expect(url).toMatch(/^data:image\/png;base64,/);
  });
});

describe("uploadRender", () => {
  beforeEach(() => {
    (global as any).fetch = vi.fn(async () => ({ ok: true, json: async () => ({}) }));
  });
  it("/api/vfs/{runId}/review/_render/{lang}.png PUT을 호출한다 (path-based)", async () => {
    const blob = new Blob([new Uint8Array([1, 2])], { type: "image/png" });
    await uploadRender("run123", "ko", blob);
    const call = (global as any).fetch.mock.calls[0];
    expect(call[0]).toBe("/api/vfs/run123/review/_render/ko.png");
    const opts = call[1];
    expect(opts.method).toBe("PUT");
    const body = JSON.parse(opts.body);
    expect(body.content_encoding).toBe("base64");
    expect(body.mime).toBe("image/png");
    expect(typeof body.content).toBe("string");
  });
  it("non-ok response → throw", async () => {
    (global as any).fetch = vi.fn(async () => ({ ok: false, status: 500 }));
    const blob = new Blob([new Uint8Array([1])], { type: "image/png" });
    await expect(uploadRender("r1", "ko", blob)).rejects.toThrow(/500/);
  });
});

describe("renderAndUploadAll graceful skip", () => {
  beforeEach(() => {
    // data URL fetch는 실제 Blob을 돌려주고, VFS PUT만 분기 — en.png는 500으로
    // 실패시켜 graceful skip 검증.
    (global as any).fetch = vi.fn(async (url: string) => {
      if (typeof url === "string" && url.startsWith("data:")) {
        return {
          ok: true,
          blob: async () => new Blob([new Uint8Array([1, 2, 3])], { type: "image/png" }),
        };
      }
      if (typeof url === "string" && url.includes("/en.png")) {
        return { ok: false, status: 500 };
      }
      return { ok: true, json: async () => ({}) };
    });
  });
  it("한 lang이 실패해도 다른 lang은 진행 (성공한 lang만 반환)", async () => {
    const uploaded = await renderAndUploadAll("r1", {
      ko: { objects: [] },
      en: { objects: [] },
    });
    expect(uploaded).toEqual(["ko"]);
  });
});
