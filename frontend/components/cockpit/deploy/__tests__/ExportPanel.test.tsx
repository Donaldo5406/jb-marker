import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

const collectExportItems = vi.fn();
const buildCampaignZip = vi.fn();
const buildCampaignManifest = vi.fn((..._a: unknown[]) => ({}));
const triggerDownload = vi.fn();
vi.mock("@/lib/deployExport", () => ({
  collectExportItems: (...a: unknown[]) => collectExportItems(...a),
  buildCampaignZip: (...a: unknown[]) => buildCampaignZip(...a),
  buildCampaignManifest: (...a: unknown[]) => buildCampaignManifest(...a),
  triggerDownload: (...a: unknown[]) => triggerDownload(...a),
}));

import { ExportPanel } from "../ExportPanel";

beforeEach(() => {
  vi.clearAllMocks();
  buildCampaignZip.mockResolvedValue(new Blob(["z"]));
});

describe("ExportPanel", () => {
  it("disables button + shows empty hint when no items", () => {
    collectExportItems.mockReturnValue([]);
    render(<ExportPanel runId="r" nodes={[]} title={null} channels={[]} eligibility={null} gate={null} />);
    expect(screen.getByText(/아직 export할 산출물이 없습니다/)).toBeInTheDocument();
    expect(screen.getByTestId("export-zip-btn")).toBeDisabled();
  });

  it("shows category summary and builds zip on click", async () => {
    collectExportItems.mockReturnValue([
      { rest: "design/final/ko/main.png", name: "main.png", category: "visual" },
      { rest: "review/report.md", name: "report.md", category: "report" },
    ]);
    render(<ExportPanel runId="r" nodes={[]} title="T" channels={["email"]} eligibility={null} gate={null} />);
    expect(screen.getByText("비주얼")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("export-zip-btn"));
    await waitFor(() => expect(buildCampaignZip).toHaveBeenCalled());
    expect(triggerDownload).toHaveBeenCalled();
  });
});
