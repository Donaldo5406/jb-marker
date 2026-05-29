import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConfirmToastView } from "../ConfirmToast";

describe("ConfirmToastView", () => {
  it("open=false면 아무것도 렌더하지 않음", () => {
    const { container } = render(
      <ConfirmToastView open={false} message="x" onConfirm={() => {}} onCancel={() => {}} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("메시지를 렌더하고 확정/취소 클릭 시 콜백 호출", () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
      <ConfirmToastView
        open
        message="작업이 저장되지 않을 수 있습니다. 이동하시겠습니까?"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );
    expect(screen.getByText("작업이 저장되지 않을 수 있습니다. 이동하시겠습니까?")).toBeInTheDocument();
    fireEvent.click(screen.getByText("이동"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByText("취소"));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
