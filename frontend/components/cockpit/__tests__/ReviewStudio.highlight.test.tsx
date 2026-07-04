import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ViolationCard } from "../review/ViolationCard";
import { ReviewStudio } from "../ReviewStudio";
import type { ReviewVerdict } from "@/lib/reviewArtifacts";

const v: ReviewVerdict = { verdict_id: "x", node: "legal", severity: "critical",
  evidence: "국내유일 최고 유일성·최상급 표현", location: { slot: "headline" } };

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

describe("ReviewStudio 시각근거·카드 동시 배치 (2026-07-05 GAP7 배치 D)", () => {
  it("bbox verdict가 로드되면 좌열 시각 패널과 우열 위반 카드가 동시에 렌더된다(토글 없음)", async () => {
    render(<ReviewStudio />);

    // 산출물 로더는 비동기(useEffect) — verdicts 반영을 기다려야 primaryImage가 채워진다.
    expect(await screen.findByTestId("hl-frame")).toBeInTheDocument();
    // 배치 C의 토글은 제거 — 카드가 우열에 상시 노출되므로 여닫을 필요가 없다.
    expect(screen.queryByText("카드 뷰")).not.toBeInTheDocument();
    expect(screen.queryByText("← 시각 뷰")).not.toBeInTheDocument();
    // 위반 카드(법률 섹션)가 시각 패널과 '동시에' 보인다 — 겹침 없는 2열 배치의 계약.
    expect(screen.getByLabelText("법률 검토")).toBeInTheDocument();
    expect(screen.getByText("하이라이트 대상 문구")).toBeInTheDocument();
  });
});
