import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { FacetField } from "../FacetField";

// jsdom에서 parallax 애니메이션 훅을 배제하고 렌더 구조만 검증한다.
vi.mock("@/components/ui/parallax-floating", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  FloatingElement: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

describe("FacetField", () => {
  it("패싯 조각 5개(SVG), 삼각 폴리곤 20개를 렌더한다", () => {
    const { container } = render(<FacetField />);
    expect(container.querySelectorAll("svg").length).toBe(5);
    expect(container.querySelectorAll("polygon").length).toBe(20);
  });
});
