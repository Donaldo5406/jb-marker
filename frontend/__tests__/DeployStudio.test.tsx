import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { CockpitProvider } from "@/components/cockpit/CockpitProvider";
import { DeployStudio } from "@/components/cockpit/DeployStudio";

/** WebSocket noop — useRunSocket가 jsdom에서 throw하지 않도록. */
class NoopWS {
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
  constructor(public url: string) {}
}

function setupFetchMock() {
  global.fetch = vi.fn().mockImplementation((url: string) => {
    const u = String(url);
    if (u.includes("/deploy/setup"))
      return Promise.resolve({ ok: true, status: 200, json: async () => ({ matrix: [], step_status: "in_progress" }) });
    if (u.includes("/deploy/eligibility"))
      return Promise.resolve({ ok: true, status: 200, json: async () => ({ total: 512, eligible_count: 100, excluded_count: 412 }) });
    if (u.includes("/deploy/packages"))
      return Promise.resolve({ ok: true, status: 200, json: async () => ({ package_id: "email_ko", status: "ok" }) });
    if (u.includes("/deploy/dispatch"))
      return Promise.resolve({ ok: false, status: 402, json: async () => ({}) });
    if (u.includes("/deploy/demo-payment"))
      return Promise.resolve({ ok: true, status: 200, json: async () => ({ dev_pass: true }) });
    return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
  });
}

beforeEach(() => {
  (global as any).WebSocket = NoopWS as any;
  setupFetchMock();
  // Deploy 스튜디오는 Pro+ 엔타이틀먼트 게이트 뒤에 있다 — 통합 흐름 검증을 위해 켠다.
  window.localStorage.setItem("jbm_deploy_entitlement", "1");
});

describe("DeployStudio", () => {
  it("opens payment modal when dispatch returns 402", async () => {
    render(
      <CockpitProvider runId="r1">
        <DeployStudio />
      </CockpitProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("provider-email")).toBeInTheDocument());
    fireEvent.click(screen.getByTestId("provider-email"));
    fireEvent.click(screen.getByText("적법성 검사 실행"));
    await waitFor(() => expect(screen.getByTestId("eligibility-panel")).toBeInTheDocument());
    fireEvent.click(screen.getByText("발송 확정 (시뮬)"));
    await waitFor(() => expect(screen.queryByTestId("demo-payment-modal")).toBeInTheDocument());
  });

  it("clicking demo-pay closes modal", async () => {
    render(
      <CockpitProvider runId="r1">
        <DeployStudio />
      </CockpitProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("provider-email")).toBeInTheDocument());
    fireEvent.click(screen.getByTestId("provider-email"));
    fireEvent.click(screen.getByText("적법성 검사 실행"));
    await waitFor(() => screen.getByTestId("eligibility-panel"));
    fireEvent.click(screen.getByText("발송 확정 (시뮬)"));
    await waitFor(() => screen.getByTestId("demo-payment-modal"));
    fireEvent.click(screen.getByTestId("demo-pay-btn"));
    await waitFor(() =>
      expect(screen.queryByTestId("demo-payment-modal")).not.toBeInTheDocument(),
    );
  });
});
