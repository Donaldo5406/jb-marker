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

function VideoProbe() {
  const c = useCockpit();
  return (
    <div>
      <span data-testid="step">{c.videoStep}</span>
      <span data-testid="medium">{c.videoMedium}</span>
      <span data-testid="gate">{c.videoGate ? c.videoGate.step : "none"}</span>
      <span data-testid="bypass">{c.videoBypass.V1 ? "on" : "off"}</span>
      <span data-testid="lang">{c.videoLang}</span>
      <span data-testid="rendering">{c.videoRendering ? "yes" : "no"}</span>
      <button data-testid="advance" onClick={() => void c.runVideo("advance")}>advance</button>
      <button data-testid="render" onClick={() => void c.renderVideo()}>render</button>
      <button data-testid="to-video" onClick={() => c.setVideoMedium("video")}>to-video</button>
      <button data-testid="bypass-on" onClick={() => c.setVideoBypass("V1", true)}>bypass</button>
      <button data-testid="lang-en" onClick={() => void c.switchVideoLang("en")}>en</button>
    </div>
  );
}

describe("CockpitProvider — video 표면", () => {
  it("기본값: videoStep=V0, medium=image, gate=none", () => {
    render(<CockpitProvider runId="r1"><VideoProbe /></CockpitProvider>);
    expect(screen.getByTestId("step").textContent).toBe("V0");
    expect(screen.getByTestId("medium").textContent).toBe("image");
    expect(screen.getByTestId("gate").textContent).toBe("none");
  });

  it("runVideo: meta.step→videoStep, confirm 봉투→videoGate", async () => {
    gatewayResponder = () => jsonRes(200, {
      text: "ok", meta: { step: "V1" },
      gate: { kind: "confirm", step: "V1", critic: null, auto_advanced: [], actions: ["confirm", "regenerate"] },
    }) as any;
    render(<CockpitProvider runId="r1"><VideoProbe /></CockpitProvider>);
    fireEvent.click(screen.getByTestId("advance"));
    await waitFor(() => expect(screen.getByTestId("step").textContent).toBe("V1"));
    expect(screen.getByTestId("gate").textContent).toBe("V1");
  });

  it("setVideoMedium·setVideoBypass·switchVideoLang 상태 반영", async () => {
    render(<CockpitProvider runId="r1"><VideoProbe /></CockpitProvider>);
    fireEvent.click(screen.getByTestId("to-video"));
    await waitFor(() => expect(screen.getByTestId("medium").textContent).toBe("video"));
    fireEvent.click(screen.getByTestId("bypass-on"));
    await waitFor(() => expect(screen.getByTestId("bypass").textContent).toBe("on"));
    fireEvent.click(screen.getByTestId("lang-en"));
    await waitFor(() => expect(screen.getByTestId("lang").textContent).toBe("en"));
  });

  it("renderVideo 422(고지 미달) → 예외 삼키고 rendering 플래그 복구", async () => {
    gatewayResponder = (body) =>
      (body.action === "render"
        ? jsonRes(422, { detail: "disclosure too short" })
        : jsonRes(200, { text: "", meta: {}, gate: null })) as any;
    render(<CockpitProvider runId="r1"><VideoProbe /></CockpitProvider>);
    fireEvent.click(screen.getByTestId("render"));
    await waitFor(() => expect(screen.getByTestId("rendering").textContent).toBe("no"));
  });
});
