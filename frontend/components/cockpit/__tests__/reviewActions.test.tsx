import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, act } from "@testing-library/react";
import { CockpitProvider, useCockpit, type CockpitContextValue } from "../CockpitProvider";

/** sceneRender 모듈을 mock — renderAndUploadAll 호출 여부·인자만 검증한다. */
const renderAndUploadAllMock = vi.fn(async (_runId: string, _scenes: Record<string, any>) => []);
vi.mock("@/lib/sceneRender", () => ({
  renderAndUploadAll: (...args: [string, Record<string, any>]) => renderAndUploadAllMock(...args),
}));

class NoopWS {
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
  constructor(public url: string) {}
}

/** vfsList → 2 lang scene 파일을 가진 트리, vfsGet → 빈 scene JSON, gateway → meta.step 반환. */
function installFetch() {
  const gatewayCalls: any[] = [];
  const fetchMock = vi.fn(async (input: any, init?: any) => {
    const url = String(input);
    const method = (init?.method ?? "GET").toUpperCase();
    const body = init?.body ? JSON.parse(init.body) : undefined;
    const ok = (json: any) => ({ ok: true, status: 200, json: async () => json });

    if (url.endsWith("/runs") && method === "GET") return ok({ runs: [] });
    if (url.endsWith("/entitlement")) return ok({ marker: false });
    // vfsList → 2 lang scene nodes
    if (/\/vfs\/[^/]+$/.test(url) && method === "GET") {
      return ok({
        nodes: [
          { path: "design/final/ko/main.scene", mime: "application/json", source: null, meta: {}, content_text: "{\"objects\":[]}" },
          { path: "design/final/en/main.scene", mime: "application/json", source: null, meta: {}, content_text: "{\"objects\":[]}" },
        ],
      });
    }
    // vfsGet 분기 — main.scene 두 개
    if (url.includes("design/final/") && url.endsWith("/main.scene") && method === "GET") {
      return ok({ path: url, mime: "application/json", source: null, meta: {},
        content_text: JSON.stringify({ objects: [] }) });
    }
    // brain·design state GETs → 미시작
    if ((url.includes("brainstorming/") || url.includes("design/_state.json"))
        && method === "GET") {
      return { ok: false, status: 404, json: async () => ({}) };
    }
    // gateway POST → meta.step/gate 응답
    if (url.endsWith("/gateway/run") && method === "POST") {
      gatewayCalls.push(body);
      // ack/restart 액션은 단순 OK, runReview는 R1로 진입.
      if (body?.action === "ack" || body?.action === "restart") {
        return ok({ output_path: "", text: "ok", meta: { step: body.action === "restart" ? "R0" : "R1" } });
      }
      return ok({
        output_path: "", text: "검토 시작",
        meta: { step: "R1", gate: { status: "PASS", critical: 0, warning: 0 } },
      });
    }
    return ok({});
  });
  vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);
  return { gatewayCalls };
}

let captured: CockpitContextValue | null = null;
function Capture() {
  captured = useCockpit();
  return null;
}

describe("CockpitProvider review actions (M5 §8.3)", () => {
  beforeEach(() => {
    captured = null;
    renderAndUploadAllMock.mockClear();
    vi.stubGlobal("WebSocket", NoopWS as unknown as typeof WebSocket);
    window.history.replaceState(null, "", "/");
  });
  afterEach(() => { vi.restoreAllMocks(); });

  it("runReview: renderAndUploadAll 호출 + gateway studio=review is_marker=true", async () => {
    const { gatewayCalls } = installFetch();
    render(
      <CockpitProvider>
        <Capture />
      </CockpitProvider>,
    );
    await act(async () => { await captured!.openRun("r1"); });
    await act(async () => { await captured!.runReview(); });

    expect(renderAndUploadAllMock).toHaveBeenCalledTimes(1);
    const [runId, scenes] = renderAndUploadAllMock.mock.calls[0];
    expect(runId).toBe("r1");
    expect(Object.keys(scenes).sort()).toEqual(["en", "ko"]);

    const gw = gatewayCalls.find((c) => c.studio === "review" && !c.action);
    expect(gw).toBeTruthy();
    expect(gw.is_marker).toBe(true);
    expect(gw.provider).toBe("anthropic");

    // state 진행
    expect(captured!.reviewStage).toBe("R1");
    expect(captured!.reviewGate?.status).toBe("PASS");
  });

  it("ackReview: gateway action=ack + reviewAcknowledged=true", async () => {
    const { gatewayCalls } = installFetch();
    render(
      <CockpitProvider>
        <Capture />
      </CockpitProvider>,
    );
    await act(async () => { await captured!.openRun("r2"); });
    await act(async () => { await captured!.ackReview(); });

    const ack = gatewayCalls.find((c) => c.action === "ack");
    expect(ack).toBeTruthy();
    expect(ack.studio).toBe("review");
    expect(ack.is_marker).toBe(true);
    expect(captured!.reviewAcknowledged).toBe(true);
  });

  it("openRun: run 전환 시 이전 run의 ack 플래그 리셋 (§7.4)", async () => {
    installFetch();
    render(
      <CockpitProvider>
        <Capture />
      </CockpitProvider>,
    );
    // run-A 진입 후 ack 시뮬
    await act(async () => { await captured!.openRun("run-A"); });
    await act(async () => { await captured!.ackReview(); });
    expect(captured!.reviewAcknowledged).toBe(true);
    // run-B로 전환 → stale ack 플래그 리셋되어야 함(거짓 deploy unlock 방지)
    await act(async () => { await captured!.openRun("run-B"); });
    expect(captured!.reviewAcknowledged).toBe(false);
    expect(captured!.reviewStage).toBeNull();
    expect(captured!.reviewGate).toBeNull();
  });

  it("restartReview: gateway action=restart + state 리셋", async () => {
    const { gatewayCalls } = installFetch();
    render(
      <CockpitProvider>
        <Capture />
      </CockpitProvider>,
    );
    await act(async () => { await captured!.openRun("r3"); });
    // 먼저 ack한 척
    await act(async () => { await captured!.ackReview(); });
    expect(captured!.reviewAcknowledged).toBe(true);
    // restart → 리셋
    await act(async () => { await captured!.restartReview(); });

    const restart = gatewayCalls.find((c) => c.action === "restart");
    expect(restart).toBeTruthy();
    expect(restart.studio).toBe("review");
    expect(captured!.reviewStage).toBe("R0");
    expect(captured!.reviewAcknowledged).toBe(false);
    expect(captured!.reviewGate).toBeNull();
  });
});
