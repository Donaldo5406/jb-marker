import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import Pricing from "../pricing/page";

describe("Pricing", () => {
  it("3개 티어와 가격을 렌더", () => {
    render(<Pricing />);
    expect(screen.getByText("Free")).toBeTruthy();
    expect(screen.getByText("₩100,000")).toBeTruthy();
    expect(screen.getByText("₩150,000")).toBeTruthy();
  });
  it("Pro+에 Deploy 스튜디오 기능 표기", () => {
    render(<Pricing />);
    expect(screen.getByText(/Deploy 스튜디오/)).toBeTruthy();
  });
});
