import { describe, it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import { ImageFilterControls } from "../ImageFilterControls";

const noop = () => {};

describe("ImageFilterControls", () => {
  it("filters 직렬화값으로 슬라이더 초기화(밝기)", () => {
    const { getByLabelText } = render(
      <ImageFilterControls filters={[{ type: "Brightness", brightness: 0.3 }]} clipPath={undefined}
        onApplyFilters={noop} onApplyMask={noop} onApplyCrop={noop} />);
    expect((getByLabelText("밝기") as HTMLInputElement).value).toBe("0.3");
  });
  it("대비 변경 → onApplyFilters(기존 밝기 보존)", () => {
    const onApplyFilters = vi.fn();
    const { getByLabelText } = render(
      <ImageFilterControls filters={[{ type: "Brightness", brightness: 0.2 }]} clipPath={undefined}
        onApplyFilters={onApplyFilters} onApplyMask={noop} onApplyCrop={noop} />);
    fireEvent.change(getByLabelText("대비"), { target: { value: "0.5" } });
    expect(onApplyFilters).toHaveBeenCalledWith({ brightness: 0.2, contrast: 0.5, saturation: 0, blur: 0, grayscale: false });
  });
  it("흑백 체크 → onApplyFilters({grayscale:true})", () => {
    const onApplyFilters = vi.fn();
    const { getByLabelText } = render(
      <ImageFilterControls filters={undefined} clipPath={undefined}
        onApplyFilters={onApplyFilters} onApplyMask={noop} onApplyCrop={noop} />);
    fireEvent.click(getByLabelText("흑백"));
    expect(onApplyFilters).toHaveBeenCalledWith({ brightness: 0, contrast: 0, saturation: 0, blur: 0, grayscale: true });
  });
  it("보정 초기화 → 전부 기본값", () => {
    const onApplyFilters = vi.fn();
    const { getByText } = render(
      <ImageFilterControls filters={[{ type: "Blur", blur: 0.5 }]} clipPath={undefined}
        onApplyFilters={onApplyFilters} onApplyMask={noop} onApplyCrop={noop} />);
    fireEvent.click(getByText("보정 초기화"));
    expect(onApplyFilters).toHaveBeenCalledWith({ brightness: 0, contrast: 0, saturation: 0, blur: 0, grayscale: false });
  });
  it("마스크 선택 → onApplyMask(kind)", () => {
    const onApplyMask = vi.fn();
    const { getByLabelText } = render(
      <ImageFilterControls filters={undefined} clipPath={undefined}
        onApplyFilters={noop} onApplyMask={onApplyMask} onApplyCrop={noop} />);
    fireEvent.change(getByLabelText("마스크"), { target: { value: "circle" } });
    expect(onApplyMask).toHaveBeenCalledWith("circle");
  });
  it("clipPath로 마스크 초기값 반영", () => {
    const { getByLabelText } = render(
      <ImageFilterControls filters={undefined} clipPath={{ type: "ellipse", rx: 50, ry: 50 }}
        onApplyFilters={noop} onApplyMask={noop} onApplyCrop={noop} />);
    expect((getByLabelText("마스크") as HTMLSelectElement).value).toBe("circle");
  });
  it("크롭 비율 선택 → onApplyCrop(aspect)", () => {
    const onApplyCrop = vi.fn();
    const { getByLabelText } = render(
      <ImageFilterControls filters={undefined} clipPath={undefined}
        onApplyFilters={noop} onApplyMask={noop} onApplyCrop={onApplyCrop} />);
    fireEvent.change(getByLabelText("크롭 비율"), { target: { value: "1:1" } });
    expect(onApplyCrop).toHaveBeenCalledWith("1:1");
  });
});
