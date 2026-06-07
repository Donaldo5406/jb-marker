import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

const closeFile = vi.fn();
let ctx: any;
vi.mock("../CockpitProvider", () => ({ useCockpit: () => ctx }));
vi.mock("../FileContent", () => ({ FileContent: () => <div data-testid="file-content" /> }));

import { FileViewerDrawer } from "../FileViewerDrawer";

beforeEach(() => {
  closeFile.mockClear();
  ctx = {
    openFile: { path: "/r/review/report.md", content: "", mime: null, dirty: false },
    activeStudio: "review",
    runId: "r",
    closeFile,
    saveFile: vi.fn(),
    setOpenFileContent: vi.fn(),
    saveSceneJson: vi.fn(),
  };
});

describe("FileViewerDrawer", () => {
  it("review에서 openFile이 있으면 드로어를 띄운다", () => {
    render(<FileViewerDrawer />);
    expect(screen.getByTestId("file-viewer-drawer")).toBeTruthy();
    expect(screen.getByTestId("file-content")).toBeTruthy();
  });
  it("brainstorming에선 띄우지 않는다(인라인 표면 사용)", () => {
    ctx.activeStudio = "brainstorming";
    render(<FileViewerDrawer />);
    expect(screen.queryByTestId("file-viewer-drawer")).toBeNull();
  });
  it("design의 .scene은 드로어가 아닌 중앙(center)이라 띄우지 않는다", () => {
    ctx.activeStudio = "design";
    ctx.openFile = { path: "/r/design/final/ko/main.scene", content: "{}", mime: null, dirty: false };
    render(<FileViewerDrawer />);
    expect(screen.queryByTestId("file-viewer-drawer")).toBeNull();
  });
  it("백드롭 클릭/Esc로 닫힌다", () => {
    render(<FileViewerDrawer />);
    fireEvent.click(screen.getByTestId("drawer-backdrop"));
    expect(closeFile).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(closeFile).toHaveBeenCalledTimes(2);
  });
});
