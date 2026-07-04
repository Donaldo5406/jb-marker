import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ViolationCard } from "../review/ViolationCard";
import { ReviewStudio } from "../ReviewStudio";
import type { ReviewVerdict } from "@/lib/reviewArtifacts";

const v: ReviewVerdict = { verdict_id: "x", node: "legal", severity: "critical",
  evidence: "업계 최고 과장", location: { slot: "headline" } };

describe("ViolationCard pin", () => {
  it("renders pin number when provided", () => {
    render(<ViolationCard v={v} pin={1} />);
    expect(screen.getByText("1")).toBeInTheDocument();
  });
  it("omits pin when undefined", () => {
    render(<ViolationCard v={v} />);
    expect(screen.queryByText("1")).not.toBeInTheDocument();
  });
});

// --- Task 7 렌더 경로: sticky 하이라이트 패널 + 카드/시각 뷰 토글 ---
// 기존 ReviewStudio.test.tsx는 verdicts:[] 고정이라 primaryImage가 항상 null이고
// 이 렌더 경로가 CI에서 전혀 실행되지 않았다(리뷰 지적). bbox 있는 verdict를
// loadReviewVerdicts mock으로 주입해 primaryImage를 채우고 실제 토글 동작을 검증한다.
const bboxVerdict: ReviewVerdict = {
  verdict_id: "hl-1",
  node: "legal",
  severity: "critical",
  evidence: "하이라이트 대상 문구",
  location: { image: "poster.png", bbox: { x: 0.1, y: 0.1, w: 0.2, h: 0.2 } },
};

const hlMockCtx: any = {
  reviewStage: "R1",
  reviewGate: null,
  reviewAcknowledged: false,
  manifest: { run_id: "r", title: null, created_at: null, step_status: {} },
  nodes: [],
  runId: "r",
  runReview: vi.fn(async () => ({ text: "" })),
  ackReview: vi.fn(async () => {}),
  restartReview: vi.fn(async () => {}),
  setStudio: vi.fn(),
};
vi.mock("../CockpitProvider", () => ({
  useCockpit: () => hlMockCtx,
}));
// HighlightFrame은 백엔드 하이라이트 HTML을 fetch하므로 실제 네트워크를 타지 않도록 스텁으로 대체.
vi.mock("../HighlightFrame", () => ({
  HighlightFrame: () => <div data-testid="hl-frame" />,
}));
// highlightImages/numberedForImage(순수 함수)는 실제 구현 유지, 비동기 로더만 mock.
vi.mock("@/lib/reviewArtifacts", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/reviewArtifacts")>();
  return {
    ...actual,
    loadReviewVerdicts: vi.fn(async () => [bboxVerdict]),
    loadReviewReport: vi.fn(async () => null),
  };
});

describe("ReviewStudio 하이라이트 패널·뷰 토글 (Task 7 render path)", () => {
  it("bbox verdict가 로드되면 시각 패널이 마운트되고, 카드/시각 뷰 토글이 실제로 패널을 여닫는다", async () => {
    render(<ReviewStudio />);

    // 산출물 로더는 비동기(useEffect) — verdicts 반영을 기다려야 primaryImage가 채워진다.
    expect(await screen.findByTestId("hl-frame")).toBeInTheDocument();
    expect(screen.queryByText("← 시각 뷰")).not.toBeInTheDocument();

    // "카드 뷰" 클릭 → 시각 패널이 사라지고 되돌아가기 버튼이 노출된다.
    fireEvent.click(screen.getByText("카드 뷰"));
    expect(screen.queryByTestId("hl-frame")).not.toBeInTheDocument();
    expect(screen.getByText("← 시각 뷰")).toBeInTheDocument();

    // "← 시각 뷰" 클릭 → 패널이 다시 마운트된다.
    fireEvent.click(screen.getByText("← 시각 뷰"));
    expect(screen.getByTestId("hl-frame")).toBeInTheDocument();
    expect(screen.queryByText("← 시각 뷰")).not.toBeInTheDocument();
  });
});
