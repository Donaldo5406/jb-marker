import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { PreDeployReview } from "../PreDeployReview";
import type { ReviewVerdict } from "@/lib/reviewArtifacts";

const v = (node: "legal" | "i18n", severity: "critical" | "warning"): ReviewVerdict => ({ node, severity });

describe("PreDeployReview", () => {
  it("shows neutral 검토 미실행 when no gate and no verdicts", () => {
    render(<PreDeployReview designDone={false} gate={null} verdicts={[]} />);
    expect(screen.getByText("검토 미실행")).toBeInTheDocument();
  });

  it("renders gate status and design state", () => {
    render(<PreDeployReview designDone gate={{ status: "PASS", critical: 0, warning: 0 }} verdicts={[]} />);
    expect(screen.getByText(/Design 완료/)).toBeInTheDocument();
    expect(screen.getByText(/법령 PASS/)).toBeInTheDocument();
  });

  it("renders violation chips from verdicts", () => {
    const verdicts = [v("legal", "critical"), v("i18n", "warning"), v("i18n", "warning")];
    render(<PreDeployReview designDone gate={{ status: "BLOCKED", critical: 1, warning: 2 }} verdicts={verdicts} />);
    expect(screen.getByTestId("violation-chips")).toBeInTheDocument();
    expect(screen.getByText("법령 critical 1")).toBeInTheDocument();
    expect(screen.getByText("i18n warning 2")).toBeInTheDocument();
  });
});
