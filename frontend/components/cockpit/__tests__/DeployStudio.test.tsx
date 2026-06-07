import { render, screen } from "@testing-library/react";
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
});
