import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ProviderGrid, type ProviderEntry } from "@/components/cockpit/deploy/ProviderGrid";

const seed: ProviderEntry[] = [
  { id: "email", name: "이메일", logo_path: "/providers/email.svg", channel_type: "email", adapter_status: "stub", priority: 1 },
  { id: "kakao", name: "카카오", logo_path: "/providers/kakao.svg", channel_type: "messenger", adapter_status: "stub", priority: 2 },
];

describe("ProviderGrid", () => {
  it("renders providers sorted by priority", () => {
    render(<ProviderGrid providers={seed} selected={[]} onChange={() => {}} />);
    const buttons = screen.getAllByRole("button");
    expect(buttons[0]).toHaveAttribute("data-testid", "provider-email");
    expect(buttons[1]).toHaveAttribute("data-testid", "provider-kakao");
  });

  it("toggles selection on click", () => {
    const onChange = vi.fn();
    render(<ProviderGrid providers={seed} selected={[]} onChange={onChange} />);
    fireEvent.click(screen.getByTestId("provider-email"));
    expect(onChange).toHaveBeenCalledWith(["email"]);
  });

  it("deselects when already selected", () => {
    const onChange = vi.fn();
    render(<ProviderGrid providers={seed} selected={["email"]} onChange={onChange} />);
    fireEvent.click(screen.getByTestId("provider-email"));
    expect(onChange).toHaveBeenCalledWith([]);
  });

  it("shows stub badge", () => {
    render(<ProviderGrid providers={seed} selected={[]} onChange={() => {}} />);
    expect(screen.getAllByText("stub").length).toBe(2);
  });
});
