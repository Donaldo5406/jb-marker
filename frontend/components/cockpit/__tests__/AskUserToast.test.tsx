import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AskUserToastView } from "../AskUserToast";

describe("AskUserToastView", () => {
  it("질문과 옵션을 렌더하고 선택 시 onSelect 호출", () => {
    const onSelect = vi.fn();
    render(<AskUserToastView ask={{ trigger: "b", question: "plan으로?", options: ["예", "아니오"] }}
            onSelect={onSelect} onClose={() => {}} />);
    expect(screen.getByText("plan으로?")).toBeInTheDocument();
    fireEvent.click(screen.getByText("예"));
    expect(onSelect).toHaveBeenCalledWith("예");
  });

  it("ask가 null이면 아무것도 렌더하지 않음", () => {
    const { container } = render(<AskUserToastView ask={null} onSelect={() => {}} onClose={() => {}} />);
    expect(container.firstChild).toBeNull();
  });
});
