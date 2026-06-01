import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { EditorPane } from "@/components/cockpit/EditorPane";
import * as ctx from "@/components/cockpit/CockpitProvider";

vi.mock("@/components/cockpit/CodeView", () => ({
  CodeView: ({ name }: { name: string }) => <div data-testid="codeview">code:{name}</div>,
}));
vi.mock("@/components/cockpit/MarkdownView", () => ({
  MarkdownView: () => <div data-testid="mdview">md</div>,
}));
vi.mock("@/components/cockpit/FabricEditor", () => ({
  FabricEditor: () => <div data-testid="fabric">fabric</div>,
}));

function mockCockpit(file: any, over: Partial<ctx.CockpitContextValue> = {}) {
  vi.spyOn(ctx, "useCockpit").mockReturnValue({
    openFile: file, loadingPath: null,
    saveFile: vi.fn(), closeFile: vi.fn(), setOpenFileContent: vi.fn(), saveSceneJson: vi.fn(),
    ...over,
  } as unknown as ctx.CockpitContextValue);
}

beforeEach(() => vi.restoreAllMocks());

const JSON_FILE = { path: "/r1/design/rough/layout.spec.json", content: '{"a":1}', mime: "application/json", dirty: false };

describe("EditorPane 코드 읽기/소스 토글", () => {
  it(".json은 기본 READ → CodeView 표시 + 파일타입 배지", async () => {
    mockCockpit(JSON_FILE);
    render(<EditorPane />);
    expect(await screen.findByTestId("codeview")).toBeTruthy();
    expect(screen.getByText("{}")).toBeTruthy(); // 배지 라벨
  });
  it("소스 토글 → textarea 편집 가능", async () => {
    mockCockpit(JSON_FILE);
    render(<EditorPane />);
    await screen.findByTestId("codeview");
    fireEvent.click(screen.getByRole("button", { name: /소스/ }));
    expect(screen.getByRole("textbox")).toBeTruthy();
  });
  it("복사 버튼 → clipboard에 파일 내용", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    mockCockpit(JSON_FILE);
    render(<EditorPane />);
    await screen.findByTestId("codeview");
    fireEvent.click(screen.getByRole("button", { name: "내용 복사" }));
    expect(writeText).toHaveBeenCalledWith('{"a":1}');
  });
  it(".scene는 Fabric 유지(코드뷰 미적용)", async () => {
    mockCockpit({ path: "/r1/design/final/ko/main.scene", content: "{}", mime: "application/json", dirty: false });
    render(<EditorPane />);
    expect(await screen.findByTestId("fabric")).toBeTruthy();
    expect(screen.queryByTestId("codeview")).toBeNull();
  });
  it("다른 코드 파일로 바뀌면 codeMode가 read로 리셋된다(CodeView 재표시)", async () => {
    mockCockpit(JSON_FILE);
    const { rerender } = render(<EditorPane />);
    await screen.findByTestId("codeview");
    // 소스 모드로 전환 → textarea
    fireEvent.click(screen.getByRole("button", { name: /소스/ }));
    expect(screen.getByRole("textbox")).toBeTruthy();
    // 다른 .json 파일로 교체 → 파일 변경 effect가 codeMode를 read로 리셋
    const OTHER = { path: "/r1/design/rough/other.json", content: '{"b":2}', mime: "application/json", dirty: false };
    mockCockpit(OTHER);
    rerender(<EditorPane />);
    expect(await screen.findByTestId("codeview")).toBeTruthy();
  });
});
