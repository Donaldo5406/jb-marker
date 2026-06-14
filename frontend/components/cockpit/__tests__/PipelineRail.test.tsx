import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PipelineRail, VIDEO_STEPS } from "../PipelineRail";

describe("PipelineRail", () => {
  it("현재 step 세그먼트가 active", () => {
    render(<PipelineRail step="S1" onAdvance={() => {}} onRegenerate={() => {}} />);
    expect(screen.getByTestId("step-seg-S1").dataset.state).toBe("active");
  });

  it("다음/재생성 콜백 호출", () => {
    const adv = vi.fn();
    const reg = vi.fn();
    render(<PipelineRail step="S1" onAdvance={adv} onRegenerate={reg} />);
    fireEvent.click(screen.getByText(/다음 단계/));
    expect(adv).toHaveBeenCalled();
    fireEvent.click(screen.getByText("재생성"));
    expect(reg).toHaveBeenCalled();
  });

  it("done이면 액션 버튼 숨김", () => {
    render(<PipelineRail step="done" onAdvance={() => {}} onRegenerate={() => {}} />);
    expect(screen.queryByText(/다음 단계/)).toBeNull();
    expect(screen.queryByText("재생성")).toBeNull();
  });

  it("게이트 정지 시 확정 라벨과 critic pass 뱃지를 보인다", () => {
    render(
      <PipelineRail
        step="S1"
        gate={{ step: "S1", critic: { passed: true, issues: [], scores: { avg: 4.2, scores: {} } }, auto_advanced: [], actions: ["confirm", "regenerate"] }}
        onAdvance={() => {}}
        onRegenerate={() => {}}
      />,
    );
    expect(screen.getByRole("button", { name: /확정/ })).toBeInTheDocument();
    expect(screen.getByText(/4\.2|pass|통과/i)).toBeInTheDocument();
  });

  it("설정 토글 버튼이 onToggleSettings를 호출하고 settingsOpen을 반영한다", () => {
    const toggle = vi.fn();
    render(
      <PipelineRail
        step="S1"
        onAdvance={() => {}}
        onRegenerate={() => {}}
        settingsOpen
        onToggleSettings={toggle}
      />,
    );
    const btn = screen.getByRole("button", { name: /스킵 스코프 설정/ });
    expect(btn.getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(btn);
    expect(toggle).toHaveBeenCalled();
  });

  it("steps prop으로 영상 단계(V-) currentId를 매칭한다", () => {
    render(<PipelineRail step="V1" steps={VIDEO_STEPS} onAdvance={() => {}} onRegenerate={() => {}} />);
    expect(screen.getByTestId("step-seg-V1").dataset.state).toBe("active");
    expect(screen.getByTestId("step-seg-V0").dataset.state).toBe("done");
    expect(screen.getByText("콘티")).toBeInTheDocument(); // V1 라벨
  });
});
