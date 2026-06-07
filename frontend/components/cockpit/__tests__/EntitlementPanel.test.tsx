import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

const toggleEntitlement = vi.fn();
const toggleDeploy = vi.fn();
let ctx: any;
vi.mock("../CockpitProvider", () => ({ useCockpit: () => ctx }));

import { EntitlementPanel } from "../EntitlementPanel";

beforeEach(() => {
  toggleEntitlement.mockClear();
  toggleDeploy.mockClear();
  ctx = { entitlement: { marker: false, deploy: false }, toggleEntitlement, toggleDeploy };
});

describe("EntitlementPanel", () => {
  it("Marker·Deploy 토글 2개를 렌더", () => {
    render(<EntitlementPanel />);
    expect(screen.getByTestId("entitlement-toggle")).toBeTruthy();
    expect(screen.getByTestId("deploy-toggle")).toBeTruthy();
  });
  it("Deploy 토글 클릭 시 toggleDeploy 호출", () => {
    render(<EntitlementPanel />);
    fireEvent.click(screen.getByTestId("deploy-toggle"));
    expect(toggleDeploy).toHaveBeenCalled();
  });
});
