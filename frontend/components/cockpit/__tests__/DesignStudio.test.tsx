import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

let ctx: any;
vi.mock("../CockpitProvider", () => ({ useCockpit: () => ctx }));
vi.mock("../ChatPane", () => ({ ChatPane: () => <div data-testid="chat-pane" /> }));
vi.mock("../FileContent", () => ({ FileContent: () => <div data-testid="file-content" /> }));
vi.mock("../FileTree", () => ({ FileTree: () => <div data-testid="file-tree" /> }));
// fallback을 그대로 렌더(placeholder 문구 검증 유지)하면서 refreshKey 배선을 노출.
vi.mock("../LayoutPreview", () => ({
  LayoutPreview: (p: any) => (
    <div data-testid="layout-preview" data-refresh-key={String(p.refreshKey)}>{p.fallback}</div>
  ),
}));

import { DesignStudio } from "../DesignStudio";

beforeEach(() => {
  ctx = {
    designStep: "S1",
    designGate: null,
    designRev: 0,
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
  it("designRev 변화가 refreshKey에 반영된다(같은 step/gate에서 프리뷰 재fetch 트리거)", () => {
    const { rerender } = render(<DesignStudio />);
    const key0 = screen.getByTestId("layout-preview").getAttribute("data-refresh-key");
    expect(key0).toBe("S1::0");
    ctx = { ...ctx, designRev: 1 };   // step·gate 불변, rev만 증가(게이트 내 regenerate/챗 교정)
    rerender(<DesignStudio />);
    const key1 = screen.getByTestId("layout-preview").getAttribute("data-refresh-key");
    expect(key1).toBe("S1::1");
    expect(key1).not.toBe(key0);
  });
});
