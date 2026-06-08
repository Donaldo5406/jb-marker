import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { IntroSection } from "@/components/landing/IntroSection";

describe("IntroSection 단계 앵커", () => {
  it("각 단계 카드에 앵커 id(step-planning/step-design/step-review)가 있다", () => {
    const { container } = render(<IntroSection />);
    expect(container.querySelector("#step-planning")).not.toBeNull();
    expect(container.querySelector("#step-design")).not.toBeNull();
    expect(container.querySelector("#step-review")).not.toBeNull();
  });

  it("상위 #pipeline 섹션 앵커는 유지된다", () => {
    const { container } = render(<IntroSection />);
    expect(container.querySelector("#pipeline")).not.toBeNull();
  });
});
