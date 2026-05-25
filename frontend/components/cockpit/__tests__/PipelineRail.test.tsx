import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PipelineRail } from "../PipelineRail";

describe("PipelineRail", () => {
  it("현재 단계를 강조하고 다음 버튼이 runDesign(advance)를 호출", () => {
    const run = vi.fn().mockResolvedValue({ text: "ok" });
    render(
      <PipelineRail
        step="S1"
        onAdvance={() => run("advance")}
        onRegenerate={() => {}}
      />,
    );
    expect(screen.getByText(/Rough/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /다음/ }));
    expect(run).toHaveBeenCalledWith("advance");
  });

  it('step==="done"일 때 advance/재생성 버튼을 숨긴다', () => {
    render(<PipelineRail step="done" onAdvance={() => {}} onRegenerate={() => {}} />);
    expect(screen.queryByRole("button", { name: /다음/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /재생성/ })).toBeNull();
  });
});
