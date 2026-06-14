import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ProcessBar } from "../ProcessBar";

describe("ProcessBar", () => {
  it("4단계 라벨을 렌더하고 blocked 단계에 잠금 표식", () => {
    render(<ProcessBar stepStatus={{ deploy: "blocked" }} active="brainstorming" onSelect={() => {}} />);
    expect(screen.getByText(/brainstorming/i)).toBeInTheDocument();
    expect(screen.getByText(/design/i)).toBeInTheDocument();
    expect(screen.getByText(/review/i)).toBeInTheDocument();
    expect(screen.getByText(/deploy/i)).toBeInTheDocument();
    // blocked 단계는 aria-disabled 또는 data-status="blocked"
    expect(screen.getByTestId("step-deploy").dataset.status).toBe("blocked");
  });
  it("medium=image(기본) → 가운데 제작 슬롯은 design", () => {
    render(<ProcessBar stepStatus={{}} active="brainstorming" onSelect={() => {}} medium="image" />);
    expect(screen.getByTestId("step-design")).toBeInTheDocument();
    expect(screen.queryByTestId("step-video")).toBeNull();
  });
  it("medium=video → 가운데 제작 슬롯이 video로 스왑(라벨·testid·data-medium)", () => {
    render(<ProcessBar stepStatus={{}} active="video" onSelect={() => {}} medium="video" />);
    const cell = screen.getByTestId("step-video");
    expect(cell).toBeInTheDocument();
    expect(screen.queryByTestId("step-design")).toBeNull();
    expect(screen.getByText(/video/i)).toBeInTheDocument();
    expect(cell.dataset.medium).toBe("video");
    expect(cell.getAttribute("aria-current")).toBe("step"); // active=video
  });
  it("제작 슬롯 클릭 시 onSelect(스왑된 스튜디오) 호출", () => {
    const onSelect = vi.fn();
    render(<ProcessBar stepStatus={{}} active="brainstorming" onSelect={onSelect} medium="video" />);
    fireEvent.click(screen.getByTestId("step-video"));
    expect(onSelect).toHaveBeenCalledWith("video");
  });
});
