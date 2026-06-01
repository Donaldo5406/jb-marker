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

  it("게이트 정지 시 확정 라벨과 critic pass 뱃지를 보인다", () => {
    render(
      <PipelineRail
        step="S1"
        gate={{ step: "S1", critic: { pass: true, avg: 4.2 }, auto_advanced: [] }}
        onAdvance={() => {}}
        onRegenerate={() => {}}
      />,
    );
    expect(screen.getByRole("button", { name: /확정/ })).toBeInTheDocument();
    expect(screen.getByText(/4\.2|pass|통과/i)).toBeInTheDocument();
  });

  it("게이트 없으면 기존 '다음 단계' 라벨", () => {
    render(<PipelineRail step="S1" gate={null} onAdvance={() => {}} onRegenerate={() => {}} />);
    expect(screen.getByRole("button", { name: /다음/ })).toBeInTheDocument();
  });

  it("bypass 연쇄로 자동 진행된 단계를 캡션으로 통지한다", () => {
    render(
      <PipelineRail
        step="S2b"
        gate={{ step: "S2b", critic: null, auto_advanced: ["S1", "S2a"] }}
        onAdvance={() => {}}
        onRegenerate={() => {}}
      />,
    );
    expect(screen.getByText(/자동 진행/)).toBeInTheDocument();
    expect(screen.getByText(/S1/)).toBeInTheDocument();
    expect(screen.getByText(/S2a/)).toBeInTheDocument();
  });

  it("auto_advanced가 비면 자동 진행 캡션을 숨긴다", () => {
    render(
      <PipelineRail
        step="S1"
        gate={{ step: "S1", critic: { pass: true, avg: 4.2 }, auto_advanced: [] }}
        onAdvance={() => {}}
        onRegenerate={() => {}}
      />,
    );
    expect(screen.queryByText(/자동 진행/)).toBeNull();
  });
});
