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
  it("Marker 토글만 렌더(Deploy Pro+ 카드 폐기 2026-07-05)", () => {
    render(<EntitlementPanel />);
    expect(screen.getByTestId("entitlement-toggle")).toBeTruthy();
    // Deploy 엔타이틀먼트 토글은 제거됨 — Deploy는 항상 이용 가능.
    expect(screen.queryByTestId("deploy-toggle")).toBeNull();
  });
  it("Marker 토글 클릭 시 toggleEntitlement 호출", () => {
    render(<EntitlementPanel />);
    fireEvent.click(screen.getByTestId("entitlement-toggle"));
    expect(toggleEntitlement).toHaveBeenCalled();
  });
});
