import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StepProgress } from "../StepProgress";

const STEPS = [
  { id: "S0", label: "셋업" },
  { id: "S1", label: "Rough" },
  { id: "S2", label: "비주얼" },
];

describe("StepProgress", () => {
  it("현재 단계 이전은 done, 현재는 active, 이후는 pending 데이터 상태", () => {
    render(<StepProgress steps={STEPS} currentId="S1" />);
    expect(screen.getByTestId("step-seg-S0").dataset.state).toBe("done");
    expect(screen.getByTestId("step-seg-S1").dataset.state).toBe("active");
    expect(screen.getByTestId("step-seg-S2").dataset.state).toBe("pending");
  });
  it("라벨을 모두 렌더한다", () => {
    render(<StepProgress steps={STEPS} currentId="S0" />);
    expect(screen.getByText("셋업")).toBeTruthy();
    expect(screen.getByText("비주얼")).toBeTruthy();
  });
  it("알 수 없는 currentId면 전부 pending", () => {
    render(<StepProgress steps={STEPS} currentId="zzz" />);
    expect(screen.getByTestId("step-seg-S0").dataset.state).toBe("pending");
  });
});
