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
  it("dispatch 402 시 결제 모달 없이 에러 텍스트를 표기한다 (결제 표면 폐기 2026-07-04)", async () => {
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
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("발송 요청 실패"));
    expect(screen.queryByTestId("demo-payment-modal")).not.toBeInTheDocument();
    expect(screen.queryByTestId("dispatch-result")).not.toBeInTheDocument();
  });

  it("keeps channel selection across studio remount", async () => {
    function Switcher() {
      const [show, setShow] = React.useState(true);
      return (
        <div>
          <button onClick={() => setShow((s) => !s)}>toggle</button>
          {show ? <DeployStudio /> : <div>away</div>}
        </div>
      );
    }
    render(
      <CockpitProvider runId="r1">
        <Switcher />
      </CockpitProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("provider-email")).toBeInTheDocument());
    fireEvent.click(screen.getByTestId("provider-email"));
    expect(screen.getByTestId("provider-email").dataset.selected).toBe("true");
    fireEvent.click(screen.getByText("toggle"));                 // unmount DeployStudio
    await waitFor(() => expect(screen.getByText("away")).toBeInTheDocument());
    fireEvent.click(screen.getByText("toggle"));                 // remount
    await waitFor(() => expect(screen.getByTestId("provider-email")).toBeInTheDocument());
    expect(screen.getByTestId("provider-email").dataset.selected).toBe("true"); // persisted
  });
});
