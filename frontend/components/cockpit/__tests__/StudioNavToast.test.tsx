import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

const setStudio = vi.fn();
let ctx: any;
vi.mock("../CockpitProvider", () => ({ useCockpit: () => ctx }));

import { StudioNavToast } from "../StudioNavToast";

beforeEach(() => {
  setStudio.mockClear();
  ctx = {
    activeStudio: "review",
    manifest: { step_status: { review: "BLOCKED" } },
    designStep: "S0",
    reviewAcknowledged: false,
    setStudio,
  };
});

describe("StudioNavToast", () => {
  it("review BLOCKED면 Design 복귀를 권유하고 이동 클릭 시 setStudio('design')", () => {
    render(<StudioNavToast />);
    expect(screen.getByTestId("studio-nav-toast")).toBeTruthy();
    expect(screen.getByText(/Design에서 수정/)).toBeTruthy();
    fireEvent.click(screen.getByTestId("nav-go"));
    expect(setStudio).toHaveBeenCalledWith("design");
  });
  it("닫기를 누르면 사라진다", () => {
    render(<StudioNavToast />);
    fireEvent.click(screen.getByTestId("nav-dismiss"));
    expect(screen.queryByTestId("studio-nav-toast")).toBeNull();
  });
  it("권유 조건이 없으면 렌더하지 않는다", () => {
    ctx.manifest = { step_status: {} };
    render(<StudioNavToast />);
    expect(screen.queryByTestId("studio-nav-toast")).toBeNull();
  });
});
