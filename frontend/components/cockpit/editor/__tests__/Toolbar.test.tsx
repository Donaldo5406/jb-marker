// frontend/components/cockpit/editor/__tests__/Toolbar.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Toolbar } from "../Toolbar";

const baseProps = {
  canUndo: true, canRedo: false, zoom: 1, saving: false, dirty: true,
  onUndo: vi.fn(), onRedo: vi.fn(), onZoomIn: vi.fn(), onZoomOut: vi.fn(),
  onZoomFit: vi.fn(), onSave: vi.fn(), onClose: vi.fn(),
};

it("저장 클릭 → onSave", () => {
  const onSave = vi.fn();
  render(<Toolbar {...baseProps} onSave={onSave} />);
  fireEvent.click(screen.getByRole("button", { name: "scene 저장" }));
  expect(onSave).toHaveBeenCalled();
});

it("canRedo=false면 다시실행 비활성", () => {
  render(<Toolbar {...baseProps} canRedo={false} />);
  expect(screen.getByRole("button", { name: "다시 실행" })).toBeDisabled();
});

it("줌 % 표시", () => {
  render(<Toolbar {...baseProps} zoom={1.4} />);
  expect(screen.getByText("140%")).toBeInTheDocument();
});
