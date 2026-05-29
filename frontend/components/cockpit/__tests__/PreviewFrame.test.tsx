import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { PreviewFrame } from "@/components/cockpit/PreviewFrame";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({ api: { getPreviewHtml: vi.fn() } }));

describe("PreviewFrame", () => {
  it("preview HTML을 iframe srcdoc에 주입", async () => {
    (api.getPreviewHtml as any).mockResolvedValue("<html><body>PV</body></html>");
    const { container } = render(<PreviewFrame runId="r1" />);
    await waitFor(() => {
      const iframe = container.querySelector("iframe");
      expect(iframe?.getAttribute("srcdoc")).toContain("PV");
    });
  });

  it("실패 시 에러 문구", async () => {
    (api.getPreviewHtml as any).mockRejectedValue(new Error("x"));
    render(<PreviewFrame runId="r1" />);
    await waitFor(() => expect(screen.getByText(/프리뷰/)).toBeTruthy());
  });
});
