import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Button } from "@/components/ui/Button";

describe("Button", () => {
  it("renders label and applies pill radius by default", () => {
    render(<Button>체험해보기</Button>);
    const btn = screen.getByRole("button", { name: "체험해보기" });
    expect(btn).toBeInTheDocument();
    expect(btn.className).toContain("rounded-full");
  });

  it("secondary variant uses panel color", () => {
    render(<Button variant="secondary">취소</Button>);
    expect(screen.getByRole("button", { name: "취소" }).className).toContain("bg-surface-container");
  });
});
