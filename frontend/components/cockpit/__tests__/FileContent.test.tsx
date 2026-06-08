import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { FileContent } from "../FileContent";

vi.mock("../ImageView", () => ({ ImageView: () => <div data-testid="image-view" /> }));
vi.mock("../MarkdownView", () => ({ MarkdownView: ({ content }: { content: string }) => <div data-testid="md-view">{content}</div> }));
vi.mock("../CodeView", () => ({ CodeView: ({ content }: { content: string }) => <pre data-testid="code-view">{content}</pre> }));
vi.mock("../editor/DesignEditor", () => ({ DesignEditor: () => <div data-testid="design-editor" /> }));

const f = (path: string, content = "") => ({ path, content, mime: null, dirty: false });

describe("FileContent", () => {
  // MarkdownView/CodeView/DesignEditor는 next/dynamic으로 비동기 로드되므로 findBy로 대기한다
  // (정적 import인 ImageView만 동기 getBy). 기존 EditorPane.test의 관례와 동일.
  it(".md는 기본 Preview(MarkdownView) 렌더", async () => {
    render(<FileContent file={f("/r/x.md", "# hi")} runId="r" onChangeContent={() => {}} onSaveScene={() => {}} />);
    expect(await screen.findByTestId("md-view")).toBeTruthy();
  });
  it(".png는 ImageView", () => {
    render(<FileContent file={f("/r/x.png")} runId="r" onChangeContent={() => {}} onSaveScene={() => {}} />);
    expect(screen.getByTestId("image-view")).toBeTruthy();
  });
  it(".scene는 DesignEditor", async () => {
    render(<FileContent file={f("/r/main.scene", "{}")} runId="r" onChangeContent={() => {}} onSaveScene={() => {}} />);
    expect(await screen.findByTestId("design-editor")).toBeTruthy();
  });
  it(".json은 기본 read(CodeView)", async () => {
    render(<FileContent file={f("/r/a.json", "{}")} runId="r" onChangeContent={() => {}} onSaveScene={() => {}} />);
    expect(await screen.findByTestId("code-view")).toBeTruthy();
  });
});
