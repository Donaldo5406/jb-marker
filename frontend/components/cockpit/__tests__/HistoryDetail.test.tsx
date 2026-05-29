import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { HistoryDetail } from "@/components/cockpit/HistoryDetail";
import { api, type GalleryResponse } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const mod = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...mod, api: { ...mod.api, getGallery: vi.fn() } };
});
// 미디어/프리뷰 자식은 단순화(별도 단위 테스트 보유).
vi.mock("@/components/cockpit/GalleryMedia", () => ({
  GalleryMedia: ({ name }: { name: string }) => <div>media:{name}</div>,
}));
vi.mock("@/components/cockpit/PreviewFrame", () => ({
  PreviewFrame: () => <div>PREVIEW</div>,
}));

const GAL: GalleryResponse = {
  run: { run_id: "r1", title: "캠페인", created_at: null, current_step: "design",
         step_status: { brainstorming: "done", design: "active" }, languages: ["ko"] },
  sections: [
    { studio: "brainstorming", label: "기획", status: "done", has_preview: false,
      groups: [{ kind: "document", items: [
        { path: "/r1/brainstorming/spec.md", name: "spec.md", mime: "text/markdown",
          source: "marker", is_media: false, meta: {} }] }] },
    { studio: "design", label: "디자인", status: "active", has_preview: true,
      groups: [{ kind: "image", items: [
        { path: "/r1/design/design-system/components/visual/v1.png", name: "v1.png",
          mime: "image/png", source: "gemini", is_media: true, meta: {} }] }] },
    { studio: "review", label: "검토", status: "none", has_preview: false, groups: [] },
    { studio: "deploy", label: "배포", status: "none", has_preview: false, groups: [] },
  ],
};

describe("HistoryDetail", () => {
  it("섹션 라벨과 아티팩트를 렌더", async () => {
    (api.getGallery as any).mockResolvedValue(GAL);
    render(<HistoryDetail runId="r1" onBack={() => {}} onContinue={() => {}} />);
    await waitFor(() => expect(screen.getByText("기획")).toBeTruthy());
    expect(screen.getByText("디자인")).toBeTruthy();
    expect(screen.getByText("spec.md")).toBeTruthy();
    expect(screen.getByText("media:v1.png")).toBeTruthy();
  });

  it("has_preview 섹션에 PreviewFrame 노출", async () => {
    (api.getGallery as any).mockResolvedValue(GAL);
    render(<HistoryDetail runId="r1" onBack={() => {}} onContinue={() => {}} />);
    await waitFor(() => expect(screen.getByText("PREVIEW")).toBeTruthy());
  });

  it("빈 섹션은 '산출물 없음' 표시", async () => {
    (api.getGallery as any).mockResolvedValue(GAL);
    render(<HistoryDetail runId="r1" onBack={() => {}} onContinue={() => {}} />);
    await waitFor(() => expect(screen.getAllByText(/산출물이 없/).length).toBeGreaterThan(0));
  });

  it("'이어서 작업' 클릭 시 onContinue(runId)", async () => {
    (api.getGallery as any).mockResolvedValue(GAL);
    const onContinue = vi.fn();
    render(<HistoryDetail runId="r1" onBack={() => {}} onContinue={onContinue} />);
    await waitFor(() => screen.getByText("기획"));
    fireEvent.click(screen.getByRole("button", { name: /이어서 작업/ }));
    expect(onContinue).toHaveBeenCalledWith("r1");
  });
});
