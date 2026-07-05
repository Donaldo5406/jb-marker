import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

let ctx: any;
vi.mock("../CockpitProvider", () => ({ useCockpit: () => ctx }));
vi.mock("@/lib/reviewArtifacts", () => ({ loadReviewVerdicts: () => Promise.resolve([]) }));

import { DeployStudio } from "../DeployStudio";

function makeCtx(overrides: Partial<any> = {}) {
  return {
    entitlement: { marker: true, deploy: true },
    eligibility: null,
    packages: {},
    runId: "r",
    selectedProviders: [],
    setSelectedProviders: vi.fn(),
    nodes: [],
    manifest: null,
    designStep: "S0",
    reviewGate: null,
    setupDeploy: vi.fn(),
    runEligibility: vi.fn(),
    runPackagingCell: vi.fn(),
    askAdvisor: vi.fn(),
    dispatchConfirm: vi.fn(),
    selectFile: vi.fn(),
    ...overrides,
  };
}

beforeEach(() => {
  ctx = makeCtx();
});

describe("DeployStudio", () => {
  it("Pro+ 게이트 폐기(2026-07-05) — entitlement.deploy=false여도 잠금 없이 스튜디오 노출", () => {
    ctx = makeCtx({ entitlement: { marker: true, deploy: false } });
    render(<DeployStudio />);
    expect(screen.queryByTestId("deploy-locked")).toBeNull();
    expect(screen.getByTestId("deploy-studio")).toBeTruthy();
    expect(screen.getByTestId("provider-grid")).toBeTruthy();
  });

  it("Deploy 스튜디오는 항상 D0 그리드를 노출한다", () => {
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
    // 채널 선택 상태는 CockpitProvider(ctx)에서 옴 — selectedProviders로 발송 버튼 활성.
    ctx = makeCtx({
      selectedProviders: ["email"],
      eligibility: { total: 10, eligible_count: 8, excluded_count: 2 },
      dispatchConfirm: vi.fn().mockResolvedValue({
        step_status: "dispatched",
        simulation: [{ channel: "email", lang: "ko", status: "sent", recipients_count: 8 }],
      }),
    });
    render(<DeployStudio />);
    await act(async () => { fireEvent.click(screen.getByText("발송 확정 (시뮬)")); });
    const panel = await screen.findByTestId("dispatch-result");
    expect(panel.textContent).toContain("[STUB]");
    expect(panel.textContent).toContain("8");
    expect(screen.getByText("Deploy Report 보기")).toBeTruthy();
  });

  it("dispatchConfirm이 error면 결과 패널 대신 에러 텍스트를 표기한다 (결제 표면 폐기)", async () => {
    ctx = makeCtx({
      selectedProviders: ["email"],
      eligibility: { total: 10, eligible_count: 8, excluded_count: 2 },
      dispatchConfirm: vi.fn().mockResolvedValue({ error: "발송 요청 실패 (HTTP 402)" }),
    });
    render(<DeployStudio />);
    await act(async () => { fireEvent.click(screen.getByText("발송 확정 (시뮬)")); });
    expect(screen.queryByTestId("dispatch-result")).toBeNull();
    expect(screen.getByRole("alert").textContent).toContain("발송 요청 실패");
  });
});
