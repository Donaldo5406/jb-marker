import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

const setVideoMedium = vi.fn();
let ctx: any;
vi.mock("../CockpitProvider", () => ({ useCockpit: () => ctx }));
vi.mock("../ModelSelector", () => ({
  ModelSelector: () => <div data-testid="model-selector" />,
  MODELS: [
    { id: "m0", provider: "anthropic", isMarker: false, label: "A" },
    { id: "m1", provider: "anthropic", isMarker: false, label: "B" },
  ],
}));

import { ChatPane } from "../ChatPane";

const base = {
  messages: [], brainStage: "A", videoMedium: "image", setVideoMedium,
  sendChat: vi.fn(), activeStudio: "brainstorming",
};

describe("ChatPane 매체 토글", () => {
  it("brainstorming이면 이미지/영상 세그먼트 노출", () => {
    ctx = { ...base, activeStudio: "brainstorming" };
    render(<ChatPane />);
    expect(screen.getByTestId("medium-image")).toBeInTheDocument();
    expect(screen.getByTestId("medium-video")).toBeInTheDocument();
  });
  it("영상 클릭 시 setVideoMedium('video')", () => {
    ctx = { ...base, activeStudio: "brainstorming" };
    render(<ChatPane />);
    fireEvent.click(screen.getByTestId("medium-video"));
    expect(setVideoMedium).toHaveBeenCalledWith("video");
  });
  it("brainstorming이 아니면 토글 미노출", () => {
    ctx = { ...base, activeStudio: "design" };
    render(<ChatPane />);
    expect(screen.queryByTestId("medium-image")).toBeNull();
  });
});
