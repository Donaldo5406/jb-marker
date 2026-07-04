import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ViolationCard } from "../review/ViolationCard";
import type { ReviewVerdict } from "@/lib/reviewArtifacts";

const v: ReviewVerdict = { verdict_id: "x", node: "legal", severity: "critical",
  evidence: "업계 최고 과장", location: { slot: "headline" } };

describe("ViolationCard pin", () => {
  it("renders pin number when provided", () => {
    render(<ViolationCard v={v} pin={1} />);
    expect(screen.getByText("1")).toBeInTheDocument();
  });
  it("omits pin when undefined", () => {
    render(<ViolationCard v={v} />);
    expect(screen.queryByText("1")).not.toBeInTheDocument();
  });
});
