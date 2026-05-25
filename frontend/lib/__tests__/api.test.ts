import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "../api";

describe("api client", () => {
  beforeEach(() => { vi.restoreAllMocks(); });

  it("gatewayRun POSTs correct body", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ output_path: "/r/brainstorming/passthrough.md", text: "x" }),
    });
    vi.stubGlobal("fetch", fetchMock);
    await api.gatewayRun({ run_id: "r", studio: "brainstorming", prompt: "hi", provider: "fake", is_marker: false });
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/gateway\/run$/);
    expect(JSON.parse(init.body)).toMatchObject({ run_id: "r", studio: "brainstorming", is_marker: false });
  });

  it("throws with status on non-ok", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 402 }));
    await expect(api.gatewayRun({ run_id: "r", studio: "brainstorming", prompt: "x", provider: "fake", is_marker: true }))
      .rejects.toMatchObject({ status: 402 });
  });

  it("wsUrl converts http to ws", () => {
    expect(api.wsUrl("abc")).toMatch(/^ws/);
  });

  it("gatewayRun forwards answer/bypass when provided", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ output_path: "/r/brainstorming/spec.md", text: "x", ask: null }),
    });
    vi.stubGlobal("fetch", fetchMock);
    await api.gatewayRun({ run_id: "r", studio: "brainstorming", prompt: "hi",
      provider: "fake", is_marker: true, answer: "예", bypass: false });
    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(init.body)).toMatchObject({ answer: "예", bypass: false });
  });

  it("vfsGet returns text content", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ path: "/r/brainstorming/_state.json", content_text: "{\"stage\":\"A\"}" }),
    }));
    const n = await api.vfsGet("r", "brainstorming/_state.json");
    expect(n.content_text).toContain("stage");
  });
});
