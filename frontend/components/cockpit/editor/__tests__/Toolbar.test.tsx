// frontend/components/cockpit/editor/__tests__/Toolbar.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Toolbar } from "../Toolbar";

const baseProps = {
  canUndo: true, canRedo: false, zoom: 1, saving: false, dirty: true, canAlign: false,
  onUndo: vi.fn(), onRedo: vi.fn(), onZoomIn: vi.fn(), onZoomOut: vi.fn(),
  onZoomFit: vi.fn(), onSave: vi.fn(), onClose: vi.fn(),
  onAddText: vi.fn(), onAddRect: vi.fn(), onAddCircle: vi.fn(), onAddLine: vi.fn(),
  onImportImage: vi.fn(), onAlign: vi.fn(), onDistribute: vi.fn(),
};

// --- P1 회귀 가드(기존 3건 유지) ---
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

// --- P2 신규 ---
describe("Toolbar P2", () => {
  it("삽입 도구 버튼이 핸들러를 디스패치한다", () => {
    const p = { ...baseProps, onAddText: vi.fn(), onAddRect: vi.fn(), onAddCircle: vi.fn(), onAddLine: vi.fn(), onImportImage: vi.fn() };
    render(<Toolbar {...p} />);
    fireEvent.click(screen.getByLabelText("텍스트 추가")); expect(p.onAddText).toHaveBeenCalled();
    fireEvent.click(screen.getByLabelText("사각형 추가")); expect(p.onAddRect).toHaveBeenCalled();
    fireEvent.click(screen.getByLabelText("원 추가")); expect(p.onAddCircle).toHaveBeenCalled();
    fireEvent.click(screen.getByLabelText("선 추가")); expect(p.onAddLine).toHaveBeenCalled();
    fireEvent.click(screen.getByLabelText("이미지 가져오기")); expect(p.onImportImage).toHaveBeenCalled();
  });
  it("canAlign=false면 정렬 버튼 미표시", () => {
    render(<Toolbar {...baseProps} canAlign={false} />);
    expect(screen.queryByLabelText("왼쪽 정렬")).toBeNull();
  });
  it("canAlign=true면 정렬/분배 버튼이 mode·axis와 함께 호출", () => {
    const p = { ...baseProps, canAlign: true, onAlign: vi.fn(), onDistribute: vi.fn() };
    render(<Toolbar {...p} />);
    fireEvent.click(screen.getByLabelText("왼쪽 정렬")); expect(p.onAlign).toHaveBeenCalledWith("left");
    fireEvent.click(screen.getByLabelText("가로 가운데 정렬")); expect(p.onAlign).toHaveBeenCalledWith("hcenter");
    fireEvent.click(screen.getByLabelText("가로 균등 분배")); expect(p.onDistribute).toHaveBeenCalledWith("h");
  });
});
