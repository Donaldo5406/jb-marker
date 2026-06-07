import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { DesignSettings } from "../DesignSettings";

describe("DesignSettings", () => {
  it("단계별 라벨과 설명을 렌더한다", () => {
    render(<DesignSettings bypass={{}} onToggle={() => {}} />);
    expect(screen.getByText("Rough")).toBeTruthy();
    expect(screen.getByText("Final")).toBeTruthy();
    expect(screen.getAllByRole("switch").length).toBe(5);
  });
  it("스위치 토글 시 onToggle(id, next)", () => {
    const onToggle = vi.fn();
    render(<DesignSettings bypass={{ S1: false }} onToggle={onToggle} />);
    fireEvent.click(screen.getByTestId("bypass-S1"));
    expect(onToggle).toHaveBeenCalledWith("S1", true);
  });
});
