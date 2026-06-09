import { describe, it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import { RasterEditModal, type FilerobotProps } from "../RasterEditModal";

// filerobot 대역: 저장/닫기 버튼으로 onSave/onClose를 발화.
function MockEditor({ onSave, onClose }: FilerobotProps) {
  return (
    <div data-testid="mock-fie">
      <button onClick={() => onSave?.(
        { imageBase64: "data:image/png;base64,QQ==", fullName: "poster.png", extension: "png", width: 10, height: 10 } as any,
        {} as any)}>fie-save</button>
      <button onClick={() => onClose?.("close", false)}>fie-close</button>
    </div>
  );
}

describe("RasterEditModal", () => {
  it("open=false면 렌더하지 않는다", () => {
    const { queryByTestId } = render(
      <RasterEditModal open={false} source="blob:x" fileName="poster.jpg"
        onApply={() => {}} onClose={() => {}} EditorComponent={MockEditor} />);
    expect(queryByTestId("mock-fie")).toBeNull();
  });

  it("저장 시 imageBase64·fullName으로 onApply 호출", () => {
    const onApply = vi.fn();
    const { getByText } = render(
      <RasterEditModal open source="blob:x" fileName="poster.jpg"
        onApply={onApply} onClose={() => {}} EditorComponent={MockEditor} />);
    fireEvent.click(getByText("fie-save"));
    expect(onApply).toHaveBeenCalledWith("data:image/png;base64,QQ==", "poster.png");
  });

  it("닫기 시 onClose 호출", () => {
    const onClose = vi.fn();
    const { getByText } = render(
      <RasterEditModal open source="blob:x" fileName="poster.jpg"
        onApply={() => {}} onClose={onClose} EditorComponent={MockEditor} />);
    fireEvent.click(getByText("fie-close"));
    expect(onClose).toHaveBeenCalled();
  });
});
