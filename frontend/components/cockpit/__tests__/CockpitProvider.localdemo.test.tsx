import * as React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { CockpitProvider, useCockpit } from "../CockpitProvider";

// 로컬 데모 회복력 2건:
//  ① NEXT_PUBLIC_DEFAULT_MOCK=1 → localStorage 미설정 시 Mock 기본 ON(키 없이 완주, 500 방지)
//  ② 챗 POST가 404(run not found) → 죽은 run 정리 + 안내(무한 무응답 방지)
class NoopWS {
  onopen: (() => void) | null = null; onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null; onerror: (() => void) | null = null;
  close = vi.fn(); constructor(public url: string) {}
}
function jsonRes(status: number, obj: any) {
  return { ok: status >= 200 && status < 300, status, json: async () => obj } as any;
}
let gatewayBodies: any[] = [];
let gatewayStatus = 200;

beforeEach(() => {
  (global as any).WebSocket = NoopWS as any;
  gatewayBodies = []; gatewayStatus = 200;
  window.localStorage.clear();
  window.history.replaceState(null, "", "/cockpit");
  global.fetch = vi.fn(async (url: any, init?: any) => {
    const u = String(url);
    if (u.includes("/gateway/run")) {
      gatewayBodies.push(init?.body ? JSON.parse(init.body) : {});
      if (gatewayStatus !== 200) return jsonRes(gatewayStatus, { detail: "run not found" });
      return jsonRes(200, { text: "목 응답", meta: {}, gate: null });
    }
    if (u.includes("/runs") && init?.method === "POST") return jsonRes(200, { run_id: "r-new" });
    return jsonRes(200, {});
  }) as any;
});
afterEach(() => { vi.unstubAllEnvs?.(); });

function Probe() {
  const c = useCockpit();
  return (
    <div>
      <span data-testid="mock">{String(c.mockMode)}</span>
      <span data-testid="runId">{c.runId ?? "null"}</span>
      <div data-testid="chat">{c.messages.map((m, i) => <p key={i}>{m.content}</p>)}</div>
      <button data-testid="start" onClick={() => void c.startRun()}>start</button>
      <button data-testid="send" onClick={() => void c.sendChat({ prompt: "안녕", provider: "anthropic", isMarker: true })}>send</button>
    </div>
  );
}

describe("로컬 데모 회복력", () => {
  it("NEXT_PUBLIC_DEFAULT_MOCK=1 + localStorage 없음 → Mock 기본 ON", async () => {
    vi.stubEnv("NEXT_PUBLIC_DEFAULT_MOCK", "1");
    render(<CockpitProvider runId="r1"><Probe /></CockpitProvider>);
    await waitFor(() => expect(screen.getByTestId("mock").textContent).toBe("true"));
  });

  it("env 미설정이면 Mock 기본 OFF(운영 기본 보존)", async () => {
    vi.stubEnv("NEXT_PUBLIC_DEFAULT_MOCK", "");
    render(<CockpitProvider runId="r1"><Probe /></CockpitProvider>);
    // 초기 마운트 이펙트가 돌 시간을 준 뒤에도 false 유지
    await act(async () => { await Promise.resolve(); });
    expect(screen.getByTestId("mock").textContent).toBe("false");
  });

  it("localStorage 저장값이 env보다 우선(사용자가 끈 상태 존중)", async () => {
    vi.stubEnv("NEXT_PUBLIC_DEFAULT_MOCK", "1");
    window.localStorage.setItem("jbm_mock_mode", "0");
    render(<CockpitProvider runId="r1"><Probe /></CockpitProvider>);
    await act(async () => { await Promise.resolve(); });
    expect(screen.getByTestId("mock").textContent).toBe("false");
  });

  it("챗 POST 404(run 만료) → runId 정리 + 만료 안내 챗", async () => {
    render(<CockpitProvider runId="r1"><Probe /></CockpitProvider>);
    fireEvent.click(screen.getByTestId("start"));
    await waitFor(() => expect(screen.getByTestId("runId").textContent).toBe("r-new"));
    gatewayStatus = 404;                       // 백엔드가 이 run을 잃음(로컬 재시작)
    fireEvent.click(screen.getByTestId("send"));
    await waitFor(() => expect(screen.getByText(/만료|Use Marker/)).toBeTruthy());
    expect(screen.getByTestId("runId").textContent).toBe("null");   // 죽은 run 비움
  });
});
