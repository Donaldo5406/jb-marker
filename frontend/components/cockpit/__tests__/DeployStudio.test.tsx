import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

let ctx: any;
vi.mock("../CockpitProvider", () => ({ useCockpit: () => ctx }));

import { DeployStudio } from "../DeployStudio";

function makeCtx(overrides: Partial<any> = {}) {
  return {
    entitlement: { marker: true, deploy: true },
    eligibility: null,
    packages: {},
    devPass: false,
    runId: "r",
    setupDeploy: vi.fn(),
    runEligibility: vi.fn(),
    runPackagingCell: vi.fn(),
    askAdvisor: vi.fn(),
    dispatchConfirm: vi.fn(),
    payDemo: vi.fn(),
    selectFile: vi.fn(),
    ...overrides,
  };
}

beforeEach(() => {
  ctx = makeCtx();
});

describe("DeployStudio", () => {
  it("deploy 엔타이틀먼트 없으면 잠금 화면을 보여준다", () => {
    ctx = makeCtx({ entitlement: { marker: true, deploy: false } });
    render(<DeployStudio />);
    expect(screen.getByTestId("deploy-locked")).toBeTruthy();
    expect(screen.queryByTestId("deploy-studio")).toBeNull();
    expect(screen.queryByTestId("provider-grid")).toBeNull();
  });

  it("deploy 엔타이틀먼트 있으면 D0 그리드를 노출한다", () => {
    render(<DeployStudio />);
    expect(screen.queryByTestId("deploy-locked")).toBeNull();
    expect(screen.getByTestId("deploy-studio")).toBeTruthy();
    expect(screen.getByTestId("provider-grid")).toBeTruthy();
  });

  it("eligibility 없으면 D0 세그먼트가 active 상태다", () => {
    render(<DeployStudio />);
    expect(screen.getByTestId("step-seg-D0").dataset.state).toBe("active");
  });

  it("발송 확정 시 결과 패널([STUB] N명)과 Report 링크를 렌더한다 (T4)", async () => {
    ctx = makeCtx({
      eligibility: { total: 10, eligible_count: 8, excluded_count: 2 },
      dispatchConfirm: vi.fn().mockResolvedValue({
        step_status: "dispatched",
        simulation: [{ channel: "email", lang: "ko", status: "sent", recipients_count: 8 }],
      }),
    });
    render(<DeployStudio />);
    fireEvent.click(screen.getByTestId("provider-email"));   // 채널 선택 → 확정 활성
    await act(async () => { fireEvent.click(screen.getByText("발송 확정 (시뮬)")); });
    const panel = await screen.findByTestId("dispatch-result");
    expect(panel.textContent).toContain("[STUB]");
    expect(panel.textContent).toContain("8");
    expect(screen.getByText("Deploy Report 보기")).toBeTruthy();
  });

  it("dispatchConfirm이 needsPayment면 결과 패널 대신 결제 모달을 연다", async () => {
    ctx = makeCtx({
      eligibility: { total: 10, eligible_count: 8, excluded_count: 2 },
      dispatchConfirm: vi.fn().mockResolvedValue({ needsPayment: true }),
    });
    render(<DeployStudio />);
    fireEvent.click(screen.getByTestId("provider-email"));
    await act(async () => { fireEvent.click(screen.getByText("발송 확정 (시뮬)")); });
    expect(screen.queryByTestId("dispatch-result")).toBeNull();
  });
});
