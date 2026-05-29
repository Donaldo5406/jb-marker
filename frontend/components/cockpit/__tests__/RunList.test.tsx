import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { RunList } from "@/components/cockpit/RunList";
import { api } from "@/lib/api";
import * as ctx from "@/components/cockpit/CockpitProvider";

vi.mock("@/lib/api", () => ({
  api: { listRuns: vi.fn(), getUsage: vi.fn() },
}));
vi.mock("@/components/cockpit/UsagePanel", () => ({
  UsagePanel: () => <div>usage</div>,
}));
vi.mock("@/components/cockpit/HistoryDetail", () => ({
  HistoryDetail: ({ runId }: { runId: string }) => <div>detail:{runId}</div>,
}));

const RUN = { run_id: "run-abcdef12", title: "캠페인", created_at: null, step_status: {} };

function mockCockpit(over: Partial<ctx.CockpitContextValue> = {}) {
  vi.spyOn(ctx, "useCockpit").mockReturnValue({
    selectedHistoryRun: null,
    viewHistoryDetail: vi.fn(),
    closeHistoryDetail: vi.fn(),
    openRun: vi.fn(),
    ...over,
  } as unknown as ctx.CockpitContextValue);
}

beforeEach(() => {
  (api.listRuns as any).mockResolvedValue({ runs: [RUN] });
});

describe("RunList 행 동작 분리", () => {
  it("행(메인) 클릭 → viewHistoryDetail(상세 진입)", async () => {
    const viewHistoryDetail = vi.fn();
    mockCockpit({ viewHistoryDetail });
    render(<RunList />);
    await waitFor(() => screen.getByText("캠페인"));
    fireEvent.click(screen.getByText("캠페인"));
    expect(viewHistoryDetail).toHaveBeenCalledWith("run-abcdef12");
  });

  it("'이어서 작업' 버튼 → openRun(워크스페이스 복귀)", async () => {
    const openRun = vi.fn();
    mockCockpit({ openRun });
    render(<RunList />);
    await waitFor(() => screen.getByText("캠페인"));
    fireEvent.click(screen.getByRole("button", { name: /이어서 작업/ }));
    expect(openRun).toHaveBeenCalledWith("run-abcdef12");
  });
});

describe("RunList ↔ HistoryDetail 토글", () => {
  it("selectedHistoryRun 있으면 HistoryDetail 렌더", async () => {
    mockCockpit({ selectedHistoryRun: "run-abcdef12" });
    render(<RunList />);
    await waitFor(() => expect(screen.getByText("detail:run-abcdef12")).toBeTruthy());
  });
});
