import * as React from "react";
import { render, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { CockpitProvider, useCockpit } from "../CockpitProvider";

// WS 스텁 — useRunSocket이 실제 연결을 시도하지 않도록(deploy 테스트 패턴).
class NoopWS {
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
  constructor(public url: string) {}
}

// 세션 api만 결정적 mock. 나머지 실제 api 메서드(vfsGet 등)는 아래 blanket fetch가 흡수.
vi.mock("@/lib/api", async (orig) => {
  const real = await orig<typeof import("@/lib/api")>();
  return {
    ...real,
    api: {
      ...real.api,
      vfsList: vi.fn().mockResolvedValue({ nodes: [] }),
      listRuns: vi.fn().mockResolvedValue({ runs: [] }),
      sessionHeartbeat: vi.fn().mockResolvedValue({
        kind: "heartbeat", exists: true, liveness: "healthy", status: "active",
        warn_at: 2000, suspend_at: 5000, expires_at: null, resumable: true,
      }),
      sessionResume: vi.fn().mockResolvedValue({ kind: "restored", run_id: "r1", studio: "design", status: "active" }),
      sessionSuspend: vi.fn().mockResolvedValue({ kind: "suspended", status: "suspended" }),
      listSessions: vi.fn().mockResolvedValue({ kind: "session_list", sessions: [
        { studio: "design", status: "active", updated_at_ms: 1000, expires_at: null },
      ] }),
    },
  };
});

let cap: ReturnType<typeof useCockpit>;
function Probe() { cap = useCockpit(); return <div>{cap.sessions.design?.liveness ?? "none"}</div>; }
function setup() {
  render(<CockpitProvider runId="r1"><Probe /></CockpitProvider>);
}

beforeEach(() => {
  vi.clearAllMocks();
  (global as any).WebSocket = NoopWS as any;
  global.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({}) });
});

describe("CockpitProvider 세션 상태/액션", () => {
  it("heartbeatSession이 wire(snake)→camel 매핑해 sessions[studio]를 채운다", async () => {
    setup();
    await act(async () => { await cap.heartbeatSession("design"); });
    expect(cap.sessions.design).toMatchObject({
      status: "active", liveness: "healthy", warnAt: 2000, suspendAt: 5000, expiresAt: null,
    });
  });

  it("exists:false heartbeat는 sessions에서 해당 studio 키를 제거한다", async () => {
    const { api } = await import("@/lib/api");
    (api.sessionHeartbeat as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      kind: "heartbeat", exists: false, status: null, resumable: false });
    setup();
    await act(async () => { await cap.heartbeatSession("design"); });
    expect(cap.sessions.design).toBeUndefined();
  });

  it("refreshSessions가 listSessions 결과를 sessionList에 싣는다", async () => {
    setup();
    await act(async () => { await cap.refreshSessions(); });
    expect(cap.sessionList).toHaveLength(1);
    expect(cap.sessionList[0]).toMatchObject({ studio: "design", status: "active" });
  });

  it("resumeSession restored면 heartbeat로 상태 동기화 후 결과 반환", async () => {
    setup();
    let res: Awaited<ReturnType<typeof cap.resumeSession>> = null;
    await act(async () => { res = await cap.resumeSession("design"); });
    expect(res).toMatchObject({ kind: "restored" });
    const { api } = await import("@/lib/api");
    expect(api.sessionHeartbeat).toHaveBeenCalledWith("r1", "design");
  });
});
