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

beforeEach(() => {
  (global as any).WebSocket = NoopWS as any;
  global.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({}) });
});

/** 소비자 프로브 — selectedProviders 읽기/쓰기. */
function Probe() {
  const c = useCockpit();
  return (
    <div>
      <button data-testid="set" onClick={() => c.setSelectedProviders(["email", "kakao"])}>set</button>
      <span data-testid="sel">{c.selectedProviders.join(",")}</span>
    </div>
  );
}

function Switcher() {
  const [show, setShow] = React.useState(true);
  return (
    <div>
      <button data-testid="toggle" onClick={() => setShow((s) => !s)}>toggle</button>
      {show ? <Probe /> : <div>away</div>}
    </div>
  );
}

describe("CockpitProvider deploy channel selection", () => {
  it("exposes selectedProviders + setter, default empty", () => {
    render(
      <CockpitProvider runId="r1">
        <Probe />
      </CockpitProvider>,
    );
    expect(screen.getByTestId("sel").textContent).toBe("");
  });

  it("persists selectedProviders across consumer remount", async () => {
    render(
      <CockpitProvider runId="r1">
        <Switcher />
      </CockpitProvider>,
    );
    fireEvent.click(screen.getByTestId("set"));
    expect(screen.getByTestId("sel").textContent).toBe("email,kakao");
    fireEvent.click(screen.getByTestId("toggle")); // unmount Probe
    await waitFor(() => expect(screen.getByText("away")).toBeInTheDocument());
    fireEvent.click(screen.getByTestId("toggle")); // remount Probe
    await waitFor(() => expect(screen.getByTestId("sel")).toBeInTheDocument());
    expect(screen.getByTestId("sel").textContent).toBe("email,kakao"); // survived remount
  });
});
