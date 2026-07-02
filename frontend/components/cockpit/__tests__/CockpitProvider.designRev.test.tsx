import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { CockpitProvider, useCockpit } from "../CockpitProvider";

class NoopWS {
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
  constructor(public url: string) {}
}

// gateway 응답을 테스트가 주입. 그 외 엔드포인트(엔타이틀먼트·vfs·manifest)는 빈 객체.
let gatewayResponder: (body: any) => { ok: boolean; status: number; json: any };

function jsonRes(status: number, obj: any) {
  return { ok: status >= 200 && status < 300, status, json: async () => obj };
}

beforeEach(() => {
  (global as any).WebSocket = NoopWS as any;
  gatewayResponder = () => jsonRes(200, { text: "", meta: {}, gate: null }) as any;
  global.fetch = vi.fn(async (url: any, init?: any) => {
    const u = String(url);
    if (u.includes("/gateway/run")) {
      const body = init?.body ? JSON.parse(init.body) : {};
      return gatewayResponder(body) as any;
    }
    return jsonRes(200, {}) as any; // entitlement/vfs/manifest 등 무해 빈응답
  }) as any;
});

function RevProbe() {
  const c = useCockpit();
  return (
    <div>
      <span data-testid="rev">{c.designRev}</span>
      <span data-testid="step">{c.designStep}</span>
      <span data-testid="gate">{c.designGate ? c.designGate.step : "none"}</span>
      <span data-testid="studio">{c.activeStudio}</span>
      <span data-testid="msgs">{c.messages.length}</span>
      <button data-testid="regen" onClick={() => void c.runDesign("regenerate")}>regen</button>
      <button data-testid="to-design" onClick={() => c.setStudio("design")}>design</button>
      <button data-testid="chat"
        onClick={() => void c.sendChat({ prompt: "고쳐줘", provider: "anthropic", isMarker: true })}>
        chat
      </button>
    </div>
  );
}

/** 게이트 정지 중 regenerate/챗 교정은 meta.step·gate가 불변 — designRev nonce가
 *  증가해야 LayoutPreview(refreshKey)가 갱신된 preview.html을 재fetch한다(회귀 방지). */
describe("CockpitProvider — designRev(시안 프리뷰 재fetch nonce)", () => {
  it("같은 step/gate에서 runDesign 2회 → designRev 1→2 (step·gate 불변)", async () => {
    // 게이트 정지 재현: 매 턴 동일한 meta.step=S1 + confirm(step=S1) 봉투.
    gatewayResponder = () => jsonRes(200, {
      text: "ok", meta: { step: "S1" },
      gate: { kind: "confirm", step: "S1", critic: null, auto_advanced: [], actions: ["confirm", "regenerate"] },
    }) as any;
    render(<CockpitProvider runId="r1"><RevProbe /></CockpitProvider>);
    expect(screen.getByTestId("rev").textContent).toBe("0");

    fireEvent.click(screen.getByTestId("regen"));
    await waitFor(() => expect(screen.getByTestId("rev").textContent).toBe("1"));

    fireEvent.click(screen.getByTestId("regen"));
    await waitFor(() => expect(screen.getByTestId("rev").textContent).toBe("2"));
    // 두 턴 내내 step·gate는 불변 — rev만이 재fetch 트리거임을 고정.
    expect(screen.getByTestId("step").textContent).toBe("S1");
    expect(screen.getByTestId("gate").textContent).toBe("S1");
  });

  it("design 스튜디오 챗 턴 → designRev 증가", async () => {
    render(<CockpitProvider runId="r1"><RevProbe /></CockpitProvider>);
    fireEvent.click(screen.getByTestId("to-design"));
    await waitFor(() => expect(screen.getByTestId("studio").textContent).toBe("design"));

    fireEvent.click(screen.getByTestId("chat"));
    await waitFor(() => expect(screen.getByTestId("rev").textContent).toBe("1"));
  });

  it("brainstorming 챗 턴 → designRev 불변(타 스튜디오 불필요 재fetch 방지)", async () => {
    render(<CockpitProvider runId="r1"><RevProbe /></CockpitProvider>);
    expect(screen.getByTestId("studio").textContent).toBe("brainstorming");

    fireEvent.click(screen.getByTestId("chat"));
    // 챗 턴 완료(유저 메시지 반영) 후에도 rev는 0 유지.
    await waitFor(() => expect(Number(screen.getByTestId("msgs").textContent)).toBeGreaterThan(0));
    expect(screen.getByTestId("rev").textContent).toBe("0");
  });
});
