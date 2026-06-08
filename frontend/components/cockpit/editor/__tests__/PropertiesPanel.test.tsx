// frontend/components/cockpit/editor/__tests__/PropertiesPanel.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PropertiesPanel } from "../PropertiesPanel";

it("선택 없음 → 안내 문구", () => {
  render(<PropertiesPanel selected={null} onChange={() => {}} />);
  expect(screen.getByText(/객체를 선택/)).toBeInTheDocument();
});

it("textbox 폰트 크기 변경 → onChange({fontSize})", () => {
  const onChange = vi.fn();
  render(<PropertiesPanel selected={{ type: "textbox", text: "x", fontSize: 48, fill: "#000", textAlign: "left", fontWeight: "normal" }} onChange={onChange} />);
  fireEvent.change(screen.getByLabelText("글자 크기"), { target: { value: "64" } });
  expect(onChange).toHaveBeenCalledWith({ fontSize: 64 });
});

it("색상 변경 → onChange({fill})", () => {
  const onChange = vi.fn();
  render(<PropertiesPanel selected={{ type: "textbox", text: "x", fontSize: 48, fill: "#000000", textAlign: "left", fontWeight: "normal" }} onChange={onChange} />);
  fireEvent.change(screen.getByLabelText("글자 색"), { target: { value: "#ff0000" } });
  expect(onChange).toHaveBeenCalledWith({ fill: "#ff0000" });
});
