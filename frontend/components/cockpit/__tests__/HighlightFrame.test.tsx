import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { HighlightFrame } from "../HighlightFrame";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({ api: { getReviewHighlightHtml: vi.fn() } }));

describe("HighlightFrame", () => {
  beforeEach(() => vi.clearAllMocks());
  it("renders iframe with fetched srcDoc", async () => {
    (api.getReviewHighlightHtml as any).mockResolvedValue("<!doctype html><body>OK</body>");
    render(<HighlightFrame runId="r1" image="p.png" />);
    const frame = await screen.findByTitle("review-highlight");
    await waitFor(() => expect(frame).toHaveAttribute("srcdoc", expect.stringContaining("OK")));
    expect(api.getReviewHighlightHtml).toHaveBeenCalledWith("r1", "p.png");
  });
  it("shows fallback on error", async () => {
    (api.getReviewHighlightHtml as any).mockRejectedValue(new Error("HTTP 500"));
    render(<HighlightFrame runId="r1" image="p.png" />);
    expect(await screen.findByText(/불러오지 못했습니다/)).toBeInTheDocument();
  });
});
