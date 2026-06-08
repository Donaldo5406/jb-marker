import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

let ctx: any;
vi.mock("../CockpitProvider", () => ({ useCockpit: () => ctx }));
vi.mock("../ChatPane", () => ({ ChatPane: () => <div data-testid="chat-pane" /> }));
vi.mock("../FileContent", () => ({ FileContent: () => <div data-testid="file-content" /> }));
vi.mock("../FileTree", () => ({ FileTree: () => <div data-testid="file-tree" /> }));

import { DesignStudio } from "../DesignStudio";

beforeEach(() => {
  ctx = {
    designStep: "S1",
    designGate: null,
    designLang: "ko",
    designBypass: {},
    setDesignBypass: vi.fn(),
    switchDesignLang: vi.fn(),
    runDesign: vi.fn().mockResolvedValue({ text: "" }),
    openFile: null,
    runId: "r",
    setOpenFileContent: vi.fn(),
    saveSceneJson: vi.fn(),
    regenConfirm: { open: false, onConfirm: vi.fn(), onCancel: vi.fn() },
  };
});

describe("DesignStudio", () => {
  it("AI 챗을 상시 렌더한다", () => {
    render(<DesignStudio />);
    expect(screen.getByTestId("chat-pane")).toBeTruthy();
  });
  it("씬 미오픈 시 중앙은 안내 빈상태", () => {
    render(<DesignStudio />);
    expect(screen.getByText(/씬이 생성되면/)).toBeTruthy();
    expect(screen.queryByTestId("file-content")).toBeNull();
  });
  it("활성 .scene이 열리면 중앙에 FileContent(에디터)", () => {
    ctx.openFile = { path: "/r/design/final/ko/main.scene", content: "{}", mime: null, dirty: false };
    render(<DesignStudio />);
    expect(screen.getByTestId("file-content")).toBeTruthy();
  });
  it("언어 스위처를 렌더한다", () => {
    render(<DesignStudio />);
    expect(screen.getByText("vi")).toBeTruthy();
  });
});
