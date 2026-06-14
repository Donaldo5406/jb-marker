import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { SessionListPanelView } from "../SessionListPanel";

describe("SessionListPanelView", () => {
  it("5 스튜디오를 모두 행으로 렌더(응답에 없으면 '미시작')", () => {
    render(<SessionListPanelView sessions={[
      { studio: "design", status: "active", updated_at_ms: 1_700_000_000_000, expires_at: null },
    ]} onRefresh={() => {}} />);
    expect(screen.getByText("디자인")).toBeInTheDocument();
    expect(screen.getByText("기획")).toBeInTheDocument();
    expect(screen.getByText("영상")).toBeInTheDocument();
    expect(screen.getByText("배포")).toBeInTheDocument();
    // design은 active 라벨, 미시작 studio는 '미시작'
    expect(screen.getByText("활성")).toBeInTheDocument();
    expect(screen.getAllByText("미시작").length).toBe(4);   // brainstorming/review/video/deploy
  });

  it("새로고침 클릭 시 onRefresh 호출", () => {
    const onRefresh = vi.fn();
    render(<SessionListPanelView sessions={[]} onRefresh={onRefresh} />);
    fireEvent.click(screen.getByRole("button", { name: /새로고침/ }));
    expect(onRefresh).toHaveBeenCalled();
  });
});
