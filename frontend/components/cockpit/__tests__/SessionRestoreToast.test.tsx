import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { SessionRestoreToastView } from "../SessionRestoreToast";

describe("SessionRestoreToastView", () => {
  it("studio가 null이면 렌더하지 않는다", () => {
    const { container } = render(<SessionRestoreToastView studio={null} onClose={() => {}} />);
    expect(container.firstChild).toBeNull();
  });

  it("studio가 있으면 복원 메시지를 띄운다", () => {
    render(<SessionRestoreToastView studio="design" onClose={() => {}} />);
    expect(screen.getByText(/세션이 복원/)).toBeInTheDocument();
  });

  it("닫기 클릭 시 onClose 호출", () => {
    const onClose = vi.fn();
    render(<SessionRestoreToastView studio="design" onClose={onClose} />);
    fireEvent.click(screen.getByLabelText("닫기"));
    expect(onClose).toHaveBeenCalled();
  });
});
