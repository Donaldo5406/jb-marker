import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { WorkspacePanel } from "@/components/cockpit/WorkspacePanel";
import * as ctx from "@/components/cockpit/CockpitProvider";

vi.mock("@/components/cockpit/FileTree", () => ({ FileTree: () => <div>tree</div> }));
vi.mock("@/components/cockpit/EditorPane", () => ({ EditorPane: () => <div>editor</div> }));
vi.mock("@/components/cockpit/ChatPane", () => ({ ChatPane: () => <div>chat</div> }));
vi.mock("@/components/cockpit/DesignStudio", () => ({ DesignStudio: () => <div>design</div> }));
vi.mock("@/components/cockpit/ReviewStudio", () => ({ ReviewStudio: () => <div>review</div> }));
vi.mock("@/components/cockpit/DeployStudio", () => ({ DeployStudio: () => <div>deploy</div> }));
vi.mock("@/components/cockpit/VideoStudio", () => ({ VideoStudio: () => <div>video-studio</div> }));
vi.mock("@/components/cockpit/StudioPlaceholder", () => ({ StudioPlaceholder: () => <div>placeholder</div> }));

function mockCockpit(over: Partial<ctx.CockpitContextValue> = {}) {
  vi.spyOn(ctx, "useCockpit").mockReturnValue({
    runId: "r1", activeStudio: "brainstorming", startRun: vi.fn(),
    ...over,
  } as unknown as ctx.CockpitContextValue);
}

beforeEach(() => vi.restoreAllMocks());

describe("WorkspacePanel 리사이즈", () => {
  it("brainstorming → 리사이즈 핸들(separator) 2개 + 3패널 렌더", () => {
    mockCockpit({ activeStudio: "brainstorming" });
    render(<WorkspacePanel />);
    expect(screen.getAllByRole("separator")).toHaveLength(2);
    expect(screen.getByText("tree")).toBeTruthy();
    expect(screen.getByText("editor")).toBeTruthy();
    expect(screen.getByText("chat")).toBeTruthy();
  });
  it("design 스튜디오 → separator 없음(현행 레이아웃)", () => {
    mockCockpit({ activeStudio: "design" });
    render(<WorkspacePanel />);
    expect(screen.queryAllByRole("separator")).toHaveLength(0);
    expect(screen.getByText("design")).toBeTruthy();
  });
  it("video 스튜디오 → VideoStudio 렌더(그리드 미사용)", () => {
    mockCockpit({ activeStudio: "video" });
    render(<WorkspacePanel />);
    expect(screen.getByText("video-studio")).toBeTruthy();
  });
});
