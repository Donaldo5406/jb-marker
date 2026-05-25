import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
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
});
