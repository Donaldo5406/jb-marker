import { describe, it, expect, vi, beforeEach } from "vitest";

// fabric을 mock
vi.mock("fabric", () => {
  return {
    fabric: {
      StaticCanvas: vi.fn().mockImplementation(() => ({
        loadFromJSON: vi.fn((_, cb) => cb()),
        renderAll: vi.fn(),
        toDataURL: vi.fn(() => "data:image/png;base64,AAAA"),
        dispose: vi.fn(),
      })),
    },
  };
});

import { renderSceneToPng, uploadRender } from "../lib/sceneRender";

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
  it("/vfs PUT을 호출한다 (path: /run/review/_render/{lang}.png)", async () => {
    const blob = new Blob([new Uint8Array([1, 2])], { type: "image/png" });
    await uploadRender("run123", "ko", blob);
    const call = (global as any).fetch.mock.calls[0];
    expect(call[0]).toContain("/vfs");
    const opts = call[1];
    expect(opts.method).toBe("PUT");
    const body = JSON.parse(opts.body);
    expect(body.path).toBe("/run123/review/_render/ko.png");
    expect(body.mime).toBe("image/png");
  });
});
