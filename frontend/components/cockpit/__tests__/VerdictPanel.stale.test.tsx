import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { VerdictPanel } from "../review/VerdictPanel";

const base = {
  acknowledged: false,
  stage: "done",
  onRun: vi.fn(), onAck: vi.fn(), onRestart: vi.fn(),
  onBackToDesign: vi.fn(), onProceedDeploy: vi.fn(),
};

describe("VerdictPanel stale (2026-07-05 GAP8)", () => {
  it("stale이면 BLOCKED 대신 '재검토 필요' 배지 + 안내 + 재검토 버튼", () => {
    render(<VerdictPanel {...base} status="BLOCKED" stale
      gate={{ critical: 4, warning: 2 }} actions={[]} />);
    expect(screen.getByText("재검토 필요")).toBeInTheDocument();
    expect(screen.queryByText(/차단되었습니다/)).not.toBeInTheDocument();
    expect(screen.getByTestId("verdict-stale-note")).toBeInTheDocument();
    expect(screen.getByTestId("gate-action-restart-stale")).toBeInTheDocument();
  });

  it("stale이어도 게이트가 없으면(첫 검토 전) 기존 '대기' 흐름 그대로", () => {
    render(<VerdictPanel {...base} stage="R0" stale gate={null} actions={[]} />);
    expect(screen.getByText("대기")).toBeInTheDocument();
    expect(screen.queryByTestId("verdict-stale-note")).not.toBeInTheDocument();
  });

  it("stale이 아니면 BLOCKED 배지·카운트 그대로(회귀 없음)", () => {
    render(<VerdictPanel {...base} status="BLOCKED"
      gate={{ critical: 4, warning: 2 }} actions={["regenerate", "restart"]} />);
    expect(screen.getByText("BLOCKED")).toBeInTheDocument();
    expect(screen.getByText(/critical 4/)).toBeInTheDocument();
  });
});
