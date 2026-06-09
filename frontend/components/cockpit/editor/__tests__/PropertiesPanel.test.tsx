import { describe, it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import { PropertiesPanel } from "../PropertiesPanel";

describe("PropertiesPanel", () => {
  it("선택 없음 안내", () => {
    const { getByText } = render(<PropertiesPanel selected={null} onChange={() => {}} />);
    expect(getByText(/객체를 선택/)).toBeTruthy();
  });
  it("textbox: 글자 색 변경 → onChange({fill})", () => {
    const onChange = vi.fn();
    const { getByLabelText } = render(
      <PropertiesPanel selected={{ type: "textbox", fill: "#000000" }} onChange={onChange} />);
    fireEvent.change(getByLabelText("글자 색"), { target: { value: "#ff0000" } });
    expect(onChange).toHaveBeenCalledWith({ fill: "#ff0000" });
  });
  it("rect: 채움/테두리/두께 편집 → onChange", () => {
    const onChange = vi.fn();
    const { getByLabelText } = render(
      <PropertiesPanel selected={{ type: "rect", fill: "#3b82f6", stroke: "#000000", strokeWidth: 0 }} onChange={onChange} />);
    fireEvent.change(getByLabelText("채움 색"), { target: { value: "#123456" } });
    expect(onChange).toHaveBeenCalledWith({ fill: "#123456" });
    fireEvent.change(getByLabelText("테두리 두께"), { target: { value: "3" } });
    expect(onChange).toHaveBeenCalledWith({ strokeWidth: 3 });
  });
  it("image: 투명도 슬라이더 → onChange({opacity})", () => {
    const onChange = vi.fn();
    const { getByLabelText } = render(
      <PropertiesPanel selected={{ type: "image", opacity: 1 }} onChange={onChange} />);
    fireEvent.change(getByLabelText("투명도"), { target: { value: "0.5" } });
    expect(onChange).toHaveBeenCalledWith({ opacity: 0.5 });
  });
});
