import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ReviewStudio } from "../ReviewStudio";

/** CockpitProvider 미사용 — useCockpit을 직접 mock해 시각 분기·콜백만 검증.
 *  (실제 액션 동작은 reviewActions.test.tsx에서 검증)
 *  산출물 로더는 읽기 전용 fetch를 하므로 mock으로 빈 결과를 강제해 테스트를 격리한다
 *  (빈 nodes·빈 verdicts·null report → 좌측 empty 상태). */
const mockCtx: any = {
  reviewStage: "R0",
  reviewGate: null,
  reviewAcknowledged: false,
  manifest: { run_id: "r", title: null, created_at: null, step_status: {} },
  nodes: [],
  runId: "r",
  runReview: vi.fn(async () => ({ text: "" })),
  ackReview: vi.fn(async () => {}),
  restartReview: vi.fn(async () => {}),
  setStudio: vi.fn(),
  remediateFromReview: vi.fn(async () => {}),
};
vi.mock("../CockpitProvider", () => ({
  useCockpit: () => mockCtx,
}));
// highlightImages/numberedForImage(Task 5, 순수함수)는 실제 구현을 유지하고
// 비동기 로더만 mock — 그래야 ReviewStudio의 파생값 계산(hlImages 등)이 깨지지 않는다.
vi.mock("@/lib/reviewArtifacts", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/reviewArtifacts")>();
  return {
    ...actual,
    loadReviewVerdicts: vi.fn(async () => []),
    loadReviewReport: vi.fn(async () => null),
  };
});

describe("ReviewStudio (M5 §8.1 · 2-col evidence)", () => {
  beforeEach(() => {
    mockCtx.reviewStage = "R0";
    mockCtx.reviewGate = null;
    mockCtx.reviewAcknowledged = false;
    mockCtx.manifest = { run_id: "r", title: null, created_at: null, step_status: {} };
    mockCtx.nodes = [];
    mockCtx.runId = "r";
    mockCtx.runReview.mockClear();
    mockCtx.ackReview.mockClear();
    mockCtx.restartReview.mockClear();
    mockCtx.setStudio.mockClear();
    mockCtx.remediateFromReview.mockClear();
  });

  it("R0 단계에서 '검토 시작' 버튼이 runReview를 호출한다", () => {
    render(<ReviewStudio />);
    // R0 셀이 active(StepProgress 세그먼트)
    expect(screen.getByTestId("step-seg-R0").dataset.state).toBe("active");
    expect(screen.getByTestId("step-seg-R1").dataset.state).toBe("pending");
    expect(screen.getByTestId("step-seg-RC")).toBeInTheDocument();
    // 검토 시작 버튼(VerdictPanel)
    const btn = screen.getByTestId("run-review");
    fireEvent.click(btn);
    expect(mockCtx.runReview).toHaveBeenCalledTimes(1);
  });

  it("중간 단계(R1/R2/R3)에서 '검토 계속' 버튼이 runReview로 완주를 재개한다", () => {
    mockCtx.reviewStage = "R2"; // 루프 중단 후 멈춘 상태 시뮬
    render(<ReviewStudio />);
    // R0 시작 버튼·done 재검토 버튼은 노출되지 않음
    expect(screen.queryByTestId("run-review")).toBeNull();
    expect(screen.queryByTestId("gate-action-restart")).toBeNull();
    // 진행 세그먼트 active
    expect(screen.getByTestId("step-seg-R2").dataset.state).toBe("active");
    // 계속 버튼 → runReview(resume) 호출
    const cont = screen.getByTestId("continue-review");
    fireEvent.click(cont);
    expect(mockCtx.runReview).toHaveBeenCalledTimes(1);
  });

  it("진행 세그먼트 R1 active", () => {
    mockCtx.reviewStage = "R1";
    render(<ReviewStudio />);
    expect(screen.getByTestId("step-seg-R1").dataset.state).toBe("active");
  });

  it("BLOCKED 상태에서 ack 버튼이 노출되지 않고 '리뷰 지적 반영해 재생성' CTA가 표시된다", () => {
    mockCtx.reviewStage = "done";
    mockCtx.manifest = { ...mockCtx.manifest, step_status: { review: "BLOCKED" } };
    mockCtx.reviewGate = { status: "BLOCKED", critical: 2, warning: 0, actions: ["regenerate", "restart"] };
    render(<ReviewStudio />);
    expect(screen.queryByTestId("gate-action-ack")).toBeNull();
    expect(screen.getByText(/critical 위반으로 배포가 차단/)).toBeInTheDocument();
    // remediate 클릭 → remediateFromReview 원클릭(D4)
    fireEvent.click(screen.getByText(/리뷰 지적 반영해 재생성/));
    expect(mockCtx.remediateFromReview).toHaveBeenCalledTimes(1);
  });

  it("done+WARN + ack 미클릭 상태에서 ack 버튼이 활성, 클릭 시 ackReview 호출", () => {
    mockCtx.reviewStage = "done";
    mockCtx.manifest = { ...mockCtx.manifest, step_status: { review: "WARN" } };
    mockCtx.reviewGate = { status: "WARN", critical: 0, warning: 1, actions: ["ack", "regenerate", "restart"] };
    mockCtx.reviewAcknowledged = false;
    render(<ReviewStudio />);
    const ack = screen.getByTestId("gate-action-ack");
    expect(ack).toBeInTheDocument();
    fireEvent.click(ack);
    expect(mockCtx.ackReview).toHaveBeenCalledTimes(1);
  });

  it("PASS 상태에서 위반 없음 메시지가 표시되고 액션 버튼은 없다(actions=[])", () => {
    mockCtx.reviewStage = "done";
    mockCtx.manifest = { ...mockCtx.manifest, step_status: { review: "PASS" } };
    mockCtx.reviewGate = { status: "PASS", critical: 0, warning: 0, actions: [] };
    render(<ReviewStudio />);
    expect(screen.queryByTestId("gate-action-ack")).toBeNull();
    expect(screen.getByText(/위반 없음/)).toBeInTheDocument();
    // 의도된 변화(P2 §3.1): PASS는 백엔드 _actions_for(PASS)=[]라 재검토 등 액션 버튼이 없다.
    expect(screen.queryByTestId("gate-action-restart")).toBeNull();
  });
});
