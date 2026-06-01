import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { CodeView } from "@/components/cockpit/CodeView";

describe("CodeView", () => {
  it(".json 내용을 hljs로 강조", () => {
    const { container } = render(<CodeView name="layout.spec.json" content={'{ "role": "cta" }'} />);
    expect(container.querySelector("code.hljs, pre.hljs")).toBeTruthy();
    expect(container.querySelector("span.hljs-attr, span.hljs-string")).toBeTruthy();
  });
  it("라인넘버 거터를 렌더", () => {
    const { container } = render(<CodeView name="a.json" content={"{\n}"} />);
    const gutter = container.querySelector("[aria-hidden].select-none");
    expect(gutter?.textContent).toContain("1");
    expect(gutter?.textContent).toContain("2");
  });
  it("대용량(>200KB)은 강조 생략(plain)", () => {
    const big = "x".repeat(200_001);
    const { container } = render(<CodeView name="a.json" content={big} />);
    expect(container.querySelector(".hljs-attr")).toBeNull();
  });
});
