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

  it("gatewayRun이 action을 body에 포함한다", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ output_path: "/p", text: "ok" }),
    });
    vi.stubGlobal("fetch", fetchMock);
    await api.gatewayRun({ run_id: "r1", studio: "design", prompt: "",
      provider: "fake", is_marker: true, action: "advance" });
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.action).toBe("advance");
  });

  it("assetUrl이 BASE 기준 vfs 경로를 만든다", () => {
    expect(api.assetUrl("r1", "design/x.png")).toContain("/vfs/r1/design/x.png");
  });

  it("getGallery는 /runs/{id}/gallery를 호출하고 JSON을 반환", async () => {
    const payload = { run: { run_id: "r1" }, sections: [] };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, json: async () => payload,
    });
    vi.stubGlobal("fetch", fetchMock);
    const out = await api.getGallery("r1");
    expect(out.run.run_id).toBe("r1");
    expect(String(fetchMock.mock.calls[0][0])).toContain("/runs/r1/gallery");
  });

  it("getPreviewHtml은 응답 텍스트(HTML)를 반환", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, text: async () => "<html>x</html>",
    });
    vi.stubGlobal("fetch", fetchMock);
    const html = await api.getPreviewHtml("r1");
    expect(html).toContain("<html>");
    expect(String(fetchMock.mock.calls[0][0])).toContain("/runs/r1/preview");
  });

  it("getPreviewHtml은 비-2xx면 throw", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false, status: 404, text: async () => "nope",
    }));
    await expect(api.getPreviewHtml("r1")).rejects.toThrow();
  });

  it("gatewayRun이 bypass_map을 body에 포함한다", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ output_path: "/p", text: "ok" }),
    });
    vi.stubGlobal("fetch", fetchMock);
    await api.gatewayRun({ run_id: "r1", studio: "design", prompt: "",
      provider: "fake", is_marker: true, action: "advance", bypass_map: { S1: true } });
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body).toMatchObject({ bypass_map: { S1: true } });
  });
});
