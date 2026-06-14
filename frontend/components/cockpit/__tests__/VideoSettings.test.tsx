import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { VideoSettings } from "../VideoSettings";

describe("VideoSettings", () => {
  it("V-단계 라벨과 설명을 렌더한다(5 스위치)", () => {
    render(<VideoSettings bypass={{}} onToggle={() => {}} />);
    expect(screen.getByText("콘티")).toBeTruthy();
    expect(screen.getByText("Final")).toBeTruthy();
    expect(screen.getAllByRole("switch").length).toBe(5);
  });
  it("스위치 토글 시 onToggle(id, next)", () => {
    const onToggle = vi.fn();
    render(<VideoSettings bypass={{ V1: false }} onToggle={onToggle} />);
    fireEvent.click(screen.getByTestId("bypass-V1"));
    expect(onToggle).toHaveBeenCalledWith("V1", true);
  });
});
