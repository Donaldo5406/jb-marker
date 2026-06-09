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
  it("textbox: 폰트 크기 변경 → onChange({fontSize}) (P1 회귀 가드)", () => {
    const onChange = vi.fn();
    const { getByLabelText } = render(
      <PropertiesPanel selected={{ type: "textbox", fontSize: 48 }} onChange={onChange} />);
    fireEvent.change(getByLabelText("글자 크기"), { target: { value: "72" } });
    expect(onChange).toHaveBeenCalledWith({ fontSize: 72 });
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
  it("image: 밝기 슬라이더 → onApplyFilters (P3)", () => {
    const onApplyFilters = vi.fn();
    const { getByLabelText } = render(
      <PropertiesPanel selected={{ type: "image", opacity: 1, filters: [] }} onChange={() => {}} onApplyFilters={onApplyFilters} />);
    fireEvent.change(getByLabelText("밝기"), { target: { value: "0.4" } });
    expect(onApplyFilters).toHaveBeenCalledWith({ brightness: 0.4, contrast: 0, saturation: 0, blur: 0, grayscale: false });
  });
});
