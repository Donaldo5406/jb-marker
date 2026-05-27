import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { UsagePanel } from "@/components/cockpit/UsagePanel";
import { api, type UsageSummary } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { ...actual.api, getUsage: vi.fn() } };
});

const mockGetUsage = api.getUsage as unknown as ReturnType<typeof vi.fn>;

const empty: UsageSummary = {
  total: { input_tokens: 0, output_tokens: 0, images: 0, cost_usd: 0, calls: 0 },
  by_step: {},
  entries: [],
};

const sample: UsageSummary = {
  total: { input_tokens: 4500, output_tokens: 1200, images: 2, cost_usd: 0.123456, calls: 4 },
  by_step: {
    advisor: {
      input_tokens: 2500, output_tokens: 800, images: 0, cost_usd: 0.0195, calls: 2,
      by_model: {
        "claude-sonnet-4-6": {
          input_tokens: 2500, output_tokens: 800, images: 0, cost_usd: 0.0195, calls: 2,
        },
      },
    },
    design: {
      input_tokens: 2000, output_tokens: 400, images: 2, cost_usd: 0.0840, calls: 2,
      by_model: {
        "gemini-2.5-flash-image": {
          input_tokens: 2000, output_tokens: 400, images: 2, cost_usd: 0.0840, calls: 2,
        },
      },
    },
  },
  entries: [],
};

describe("UsagePanel", () => {
  beforeEach(() => {
    mockGetUsage.mockReset();
  });

  it("로딩 → 빈 상태", async () => {
    mockGetUsage.mockResolvedValue(empty);
    render(<UsagePanel runId="r1" />);
    expect(screen.getByTestId("usage-loading-r1")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("usage-empty-r1")).toBeInTheDocument());
  });

  it("샘플 데이터 → 단계별 표시 + 비용 정렬", async () => {
    mockGetUsage.mockResolvedValue(sample);
    render(<UsagePanel runId="r2" />);
    await waitFor(() => expect(screen.getByTestId("usage-panel-r2")).toBeInTheDocument());
    expect(screen.getByText(/Advisor \(D2\)/)).toBeInTheDocument();
    expect(screen.getByText("Design")).toBeInTheDocument();
    expect(screen.getByText("$0.1235")).toBeInTheDocument();
    expect(screen.getByText(/in 4.5K · out 1.2K/)).toBeInTheDocument();
  });

  it("에러 → 에러 카드", async () => {
    mockGetUsage.mockRejectedValue(new Error("boom"));
    render(<UsagePanel runId="r3" />);
    await waitFor(() => expect(screen.getByTestId("usage-error-r3")).toBeInTheDocument());
  });
});
