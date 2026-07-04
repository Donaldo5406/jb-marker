import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { LayoutPreview } from "@/components/cockpit/LayoutPreview";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({ api: { vfsGet: vi.fn() } }));

const node = (html: string | null) => ({
  path: "design/rough/preview.html",
  mime: "text/html",
  source: null,
  content_text: html,
  meta: {},
});

beforeEach(() => {
  (api.vfsGet as any).mockReset();
});

describe("LayoutPreview", () => {
  it("성공 시 preview HTML을 iframe srcdoc에 주입 + 라벨 노출", async () => {
    (api.vfsGet as any).mockResolvedValue(node("<html><body>ZONE</body></html>"));
    const { container } = render(<LayoutPreview runId="r1" fallback={<div>폴백</div>} />);
    await waitFor(() => {
      const iframe = container.querySelector("iframe");
      expect(iframe?.getAttribute("srcdoc")).toContain("ZONE");
    });
    expect(
      screen.getByText(/시안 프리뷰 — 최종 생성물과 다를 수 있습니다/),
    ).toBeTruthy();
    expect(api.vfsGet as any).toHaveBeenCalledWith("r1", "design/rough/preview.html");
  });

  it("404/실패 시 fallback(placeholder) 렌더 + iframe 없음", async () => {
    (api.vfsGet as any).mockRejectedValue(
      Object.assign(new Error("HTTP 404"), { status: 404 }),
    );
    render(<LayoutPreview runId="r1" fallback={<div>디자인 캔버스 폴백</div>} />);
    await waitFor(() => expect(screen.getByText("디자인 캔버스 폴백")).toBeTruthy());
    expect(document.querySelector("iframe")).toBeNull();
  });

  it("refreshKey 변경 시 재fetch(호출 2회 + 새 HTML 반영)", async () => {
    (api.vfsGet as any).mockResolvedValue(node("<html>V1</html>"));
    const { rerender, container } = render(
      <LayoutPreview runId="r1" refreshKey="a" />,
    );
    await waitFor(() => {
      expect(container.querySelector("iframe")?.getAttribute("srcdoc")).toContain("V1");
    });
    expect((api.vfsGet as any).mock.calls.length).toBe(1);

    (api.vfsGet as any).mockResolvedValue(node("<html>V2</html>"));
    rerender(<LayoutPreview runId="r1" refreshKey="b" />);
    await waitFor(() => {
      expect(container.querySelector("iframe")?.getAttribute("srcdoc")).toContain("V2");
    });
    expect((api.vfsGet as any).mock.calls.length).toBe(2);
  });
});
