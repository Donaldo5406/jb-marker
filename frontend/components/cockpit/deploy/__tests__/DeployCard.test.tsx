import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { DeployCard } from "../DeployCard";

describe("DeployCard", () => {
  it("renders step chip, title, desc, badge, children", () => {
    render(
      <DeployCard step="D9" title="제목" desc="설명문" badge={<span>BADGE</span>}>
        <div>본문</div>
      </DeployCard>,
    );
    expect(screen.getByText("D9")).toBeInTheDocument();
    expect(screen.getByText("제목")).toBeInTheDocument();
    expect(screen.getByText("설명문")).toBeInTheDocument();
    expect(screen.getByText("BADGE")).toBeInTheDocument();
    expect(screen.getByText("본문")).toBeInTheDocument();
  });

  it("omits step chip when not provided", () => {
    render(<DeployCard title="T"><div>C</div></DeployCard>);
    expect(screen.getByTestId("deploy-card")).toBeInTheDocument();
    expect(screen.getByText("T")).toBeInTheDocument();
  });
});
