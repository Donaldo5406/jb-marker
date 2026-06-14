import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

let ctx: any;
vi.mock("../CockpitProvider", () => ({ useCockpit: () => ctx }));
vi.mock("../ChatPane", () => ({ ChatPane: () => <div data-testid="chat-pane" /> }));
vi.mock("../FileTree", () => ({ FileTree: () => <div data-testid="file-tree" /> }));
vi.mock("../PipelineRail", () => ({ PipelineRail: (p: any) => <div data-testid="pipeline-rail" data-step={p.step} /> }));

import { VideoStudio } from "../VideoStudio";

beforeEach(() => {
  ctx = {
    videoStep: "V1",
    videoGate: null,
    videoLang: "ko",
    videoBypass: {},
    setVideoBypass: vi.fn(),
    switchVideoLang: vi.fn(),
    runVideo: vi.fn().mockResolvedValue({ text: "" }),
    runId: "r",
  };
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
  it("중앙은 에디터 안내 플레이스홀더(P3)", () => {
    render(<VideoStudio />);
    expect(screen.getByText(/콘티가 생성되면/)).toBeTruthy();
  });
  it("언어 스위처를 렌더한다", () => {
    render(<VideoStudio />);
    expect(screen.getByText("vi")).toBeTruthy();
  });
});
