import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ReviewStudio } from "../ReviewStudio";

/** CockpitProvider 미사용 — useCockpit을 직접 mock해 시각 분기·콜백만 검증.
 *  (실제 액션 동작은 reviewActions.test.tsx에서 검증) */
const mockCtx: any = {
  reviewStage: "R0",
  reviewGate: null,
  reviewAcknowledged: false,
  manifest: { run_id: "r", title: null, created_at: null, step_status: {} },
  runReview: vi.fn(async () => ({ text: "" })),
  ackReview: vi.fn(async () => {}),
  restartReview: vi.fn(async () => {}),
};
vi.mock("../CockpitProvider", () => ({
  useCockpit: () => mockCtx,
}));

describe("ReviewStudio (M5 §8.1)", () => {
  beforeEach(() => {
    mockCtx.reviewStage = "R0";
    mockCtx.reviewGate = null;
    mockCtx.reviewAcknowledged = false;
    mockCtx.manifest = { run_id: "r", title: null, created_at: null, step_status: {} };
    mockCtx.runReview.mockClear();
    mockCtx.ackReview.mockClear();
    mockCtx.restartReview.mockClear();
  });

  it("R0 단계에서 '검토 시작' 버튼이 runReview를 호출한다", () => {
    render(<ReviewStudio />);
    expect(screen.getByText("ReviewStudio")).toBeInTheDocument();
    // 3 페르소나 카드
    expect(screen.getByTestId("persona-legal")).toBeInTheDocument();
    expect(screen.getByTestId("persona-i18n")).toBeInTheDocument();
    expect(screen.getByTestId("persona-reconciler")).toBeInTheDocument();
    // R0 셀이 active
    expect(screen.getByTestId("review-step-R0").dataset.active).toBe("true");
    expect(screen.getByTestId("review-step-R1").dataset.active).toBe("false");
    // 검토 시작 버튼
    const btn = screen.getByTestId("run-review");
    fireEvent.click(btn);
    expect(mockCtx.runReview).toHaveBeenCalledTimes(1);
  });

  it("BLOCKED 상태에서 ack 버튼이 노출되지 않고 차단 안내가 표시된다", () => {
    mockCtx.reviewStage = "done";
    mockCtx.manifest = { ...mockCtx.manifest, step_status: { review: "BLOCKED" } };
    mockCtx.reviewGate = { status: "BLOCKED", critical: 2, warning: 0 };
    render(<ReviewStudio />);
    expect(screen.getByTestId("gate-badge").textContent).toBe("BLOCKED");
    expect(screen.queryByTestId("ack-button")).toBeNull();
    expect(screen.getByText(/critical 위반으로 deploy 진입이 차단/)).toBeInTheDocument();
  });

  it("WARN + ack 미클릭 상태에서 ack 버튼이 활성, 클릭 시 ackReview 호출", () => {
    mockCtx.reviewStage = "done";
    mockCtx.manifest = { ...mockCtx.manifest, step_status: { review: "WARN" } };
    mockCtx.reviewGate = { status: "WARN", critical: 0, warning: 1 };
    mockCtx.reviewAcknowledged = false;
    render(<ReviewStudio />);
    const ack = screen.getByTestId("ack-button");
    expect(ack).toBeInTheDocument();
    fireEvent.click(ack);
    expect(mockCtx.ackReview).toHaveBeenCalledTimes(1);
  });

  it("PASS 상태에서 위반 없음 메시지가 표시되고 ack 버튼은 없다", () => {
    mockCtx.reviewStage = "done";
    mockCtx.manifest = { ...mockCtx.manifest, step_status: { review: "PASS" } };
    mockCtx.reviewGate = { status: "PASS", critical: 0, warning: 0 };
    render(<ReviewStudio />);
    expect(screen.getByTestId("gate-badge").textContent).toBe("PASS");
    expect(screen.queryByTestId("ack-button")).toBeNull();
    expect(screen.getByText(/위반 없음/)).toBeInTheDocument();
    // done 단계 → restart 버튼 표시
    expect(screen.getByTestId("restart-review")).toBeInTheDocument();
  });
});
