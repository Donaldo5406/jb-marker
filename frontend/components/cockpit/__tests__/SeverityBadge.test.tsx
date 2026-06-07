import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { SeverityBadge } from "../SeverityBadge";

describe("SeverityBadge", () => {
  it("critical 레벨은 critical 토큰 클래스를 단다", () => {
    render(<SeverityBadge level="critical">치명</SeverityBadge>);
    const el = screen.getByText("치명");
    expect(el.className).toContain("bg-severity-critical-bg");
    expect(el.className).toContain("text-severity-critical-fg");
  });
  it("warning/ok 레벨도 각 토큰을 단다", () => {
    const { rerender } = render(<SeverityBadge level="warning">경고</SeverityBadge>);
    expect(screen.getByText("경고").className).toContain("bg-severity-warning-bg");
    rerender(<SeverityBadge level="ok">통과</SeverityBadge>);
    expect(screen.getByText("통과").className).toContain("bg-severity-ok-bg");
  });
});
