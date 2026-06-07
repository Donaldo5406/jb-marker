import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, act } from "@testing-library/react";
import { CockpitProvider, useCockpit, type CockpitContextValue } from "../CockpitProvider";

class NoopWS {
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
  constructor(public url: string) {}
}

/** 빈 트리·미시작 상태만 응답하는 fetch. 이미지 GET이 호출되면 잡아내기 위해 url 기록. */
function installFetch() {
  const getUrls: string[] = [];
  const fetchMock = vi.fn(async (input: any, init?: any) => {
    const url = String(input);
    const method = (init?.method ?? "GET").toUpperCase();
    if (method === "GET") getUrls.push(url);
    const ok = (json: any) => ({ ok: true, status: 200, json: async () => json });
    if (url.endsWith("/runs") && method === "GET") return ok({ runs: [] });
    if (url.endsWith("/entitlement")) return ok({ marker: false });
    if (/\/vfs\/[^/]+$/.test(url) && method === "GET") return ok({ nodes: [] });
    if ((url.includes("brainstorming/") || url.includes("design/_state.json")) && method === "GET") {
      return { ok: false, status: 404, json: async () => ({}) };
    }
    return ok({});
  });
  vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);
  return { getUrls };
}

let captured: CockpitContextValue | null = null;
function Capture() {
  captured = useCockpit();
  return null;
}

describe("CockpitProvider.selectFile 이미지 분기", () => {
  beforeEach(() => {
    captured = null;
    vi.stubGlobal("WebSocket", NoopWS as unknown as typeof WebSocket);
    window.history.replaceState(null, "", "/");
  });
  afterEach(() => { vi.restoreAllMocks(); });

  it("이미지(.png)는 텍스트 fetch 없이 openFile만 세팅한다", async () => {
    const { getUrls } = installFetch();
    render(
      <CockpitProvider>
        <Capture />
      </CockpitProvider>,
    );
    await act(async () => { await captured!.openRun("r1"); });
    const pngPath = "/r1/design/design-system/components/visual/v1.png";
    await act(async () => { await captured!.selectFile(pngPath); });

    // openFile 세팅(빈 content) — ImageView가 useAuthedBlob으로 별도 로드
    expect(captured!.openFile?.path).toBe(pngPath);
    expect(captured!.openFile?.content).toBe("");
    expect(captured!.loadingPath).toBeNull();
    // PNG 경로로의 텍스트 GET(vfsGet)이 발생하지 않아야 한다("... is not valid JSON" 회피)
    expect(getUrls.some((u) => u.endsWith("v1.png"))).toBe(false);
  });
});
