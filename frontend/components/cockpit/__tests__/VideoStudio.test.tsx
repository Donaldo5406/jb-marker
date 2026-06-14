import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

let ctx: any;
vi.mock("../CockpitProvider", () => ({ useCockpit: () => ctx }));
vi.mock("../ChatPane", () => ({ ChatPane: () => <div data-testid="chat-pane" /> }));
vi.mock("../FileTree", () => ({ FileTree: () => <div data-testid="file-tree" /> }));
vi.mock("../PipelineRail", () => ({
  PipelineRail: (p: any) => <div data-testid="pipeline-rail" data-step={p.step} data-steps={(p.steps ?? []).map((s: any) => s.id).join(",")} />,
  VIDEO_STEPS: [
    { id: "V0", label: "셋업" }, { id: "V1", label: "콘티" }, { id: "V2a", label: "촬영" },
    { id: "V2b", label: "카피" }, { id: "V2c", label: "브랜드" }, { id: "V3", label: "Final" }, { id: "done", label: "완료" },
  ],
}));
vi.mock("../editor/VideoEditor", () => ({
  VideoEditor: (p: any) => <div data-testid="video-editor">{String(p.content).slice(0, 6)}</div>,
}));
vi.mock("@/lib/api", () => ({
  api: { vfsGet: vi.fn() },
}));

import { VideoStudio } from "../VideoStudio";
import { api } from "@/lib/api";

beforeEach(() => {
  ctx = {
    videoStep: "V1",
    videoGate: null,
    videoLang: "ko",
    videoBypass: {},
    videoRendering: false,
    setVideoBypass: vi.fn(),
    switchVideoLang: vi.fn(),
    runVideo: vi.fn().mockResolvedValue({ text: "" }),
    renderVideo: vi.fn().mockResolvedValue(undefined),
    saveVideoStoryboard: vi.fn().mockResolvedValue(undefined),
    runId: "r",
  };
  // 기본: storyboard 없음 → 플레이스홀더. 개별 테스트가 mockResolvedValueOnce로 덮어씀.
  (api.vfsGet as any).mockReset().mockRejectedValue(new Error("none"));
});

describe("VideoStudio", () => {
  it("PipelineRail을 videoStep으로 렌더한다", () => {
    render(<VideoStudio />);
    expect(screen.getByTestId("pipeline-rail").dataset.step).toBe("V1");
  });
  it("AI 챗을 상시 렌더한다", () => {
    render(<VideoStudio />);
    expect(screen.getByTestId("chat-pane")).toBeTruthy();
  });
  it("중앙은 storyboard 없으면 안내 플레이스홀더", () => {
    render(<VideoStudio />);
    expect(screen.getByTestId("video-canvas-empty")).toBeTruthy();
    expect(screen.getByText(/콘티가 생성되면/)).toBeTruthy();
  });
  it("언어 스위처를 렌더한다", () => {
    render(<VideoStudio />);
    expect(screen.getByText("vi")).toBeTruthy();
  });
  it("PipelineRail에 영상 단계(VIDEO_STEPS)를 주입한다", () => {
    render(<VideoStudio />);
    expect(screen.getByTestId("pipeline-rail").dataset.steps).toBe("V0,V1,V2a,V2b,V2c,V3,done");
  });
  it("storyboard 로드되면 VideoEditor 렌더", async () => {
    (api.vfsGet as any).mockResolvedValueOnce({ content_text: '{"shots":[]}' });
    render(<VideoStudio />);
    await waitFor(() => expect(screen.getByTestId("video-editor")).toBeInTheDocument());
  });
});
