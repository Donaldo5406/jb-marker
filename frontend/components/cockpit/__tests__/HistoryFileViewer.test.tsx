import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

const vfsGet = vi.fn();
vi.mock("@/lib/api", () => ({ api: { vfsGet: (...a: any[]) => vfsGet(...a) } }));
vi.mock("../MarkdownView", () => ({
  MarkdownView: ({ content }: { content: string }) => <div data-testid="md">{content}</div>,
}));
vi.mock("../CodeView", () => ({
  CodeView: ({ content }: { content: string }) => <div data-testid="code">{content}</div>,
}));

import { HistoryFileViewer } from "../HistoryFileViewer";

beforeEach(() => {
  vfsGet.mockReset();
});

describe("HistoryFileViewer", () => {
  it("run 프리픽스를 떼어 vfsGet으로 로드하고 md는 MarkdownView로 렌더한다", async () => {
    vfsGet.mockResolvedValue({ content_text: "# Plan", mime: "text/markdown" });
    render(<HistoryFileViewer runId="r1" path="/r1/brainstorming/plan.md" onClose={() => {}} />);
    const md = await screen.findByTestId("md");
    expect(md.textContent).toContain("# Plan");
    expect(vfsGet).toHaveBeenCalledWith("r1", "brainstorming/plan.md");
  });

  it("md가 아닌 파일은 CodeView로 렌더한다", async () => {
    vfsGet.mockResolvedValue({ content_text: "{}", mime: "application/json" });
    render(<HistoryFileViewer runId="r1" path="/r1/design/rough/layout.spec.json" onClose={() => {}} />);
    const code = await screen.findByTestId("code");
    expect(code.textContent).toContain("{}");
  });

  it("백드롭 클릭과 Esc로 닫힌다", async () => {
    vfsGet.mockResolvedValue({ content_text: "x", mime: "text/markdown" });
    const onClose = vi.fn();
    render(<HistoryFileViewer runId="r1" path="/r1/brainstorming/spec.md" onClose={onClose} />);
    await screen.findByTestId("md");
    fireEvent.click(screen.getByTestId("history-file-backdrop"));
    expect(onClose).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it("로드 실패 시 에러 메시지를 보인다", async () => {
    vfsGet.mockRejectedValue(new Error("nope"));
    render(<HistoryFileViewer runId="r1" path="/r1/brainstorming/plan.md" onClose={() => {}} />);
    expect(await screen.findByText("파일을 불러오지 못했습니다.")).toBeTruthy();
  });
});
