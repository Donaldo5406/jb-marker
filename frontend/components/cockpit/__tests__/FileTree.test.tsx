import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within, waitFor } from "@testing-library/react";
import { FileTree, buildTree, flattenTree, allDirKeys } from "@/components/cockpit/FileTree";
import * as ctx from "@/components/cockpit/CockpitProvider";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: { vfsPut: vi.fn().mockResolvedValue({}) },
}));

const RUN = "run1";
const NODES = [
  { path: "/run1/brainstorming/spec.md", mime: "text/markdown" },
  { path: "/run1/design/rough/layout.spec.json", mime: "application/json" },
  { path: "/run1/design/final/ko/main.scene", mime: "application/json" },
  { path: "/run1/_state.json", mime: "application/json" },
  { path: "/run1/usage/log.jsonl", mime: "application/json" },
] as any;

function mockCockpit(over: Partial<ctx.CockpitContextValue> = {}) {
  vi.spyOn(ctx, "useCockpit").mockReturnValue({
    nodes: NODES, runId: RUN, openFile: null, loadingPath: null,
    selectFile: vi.fn(),
    ...over,
  } as unknown as ctx.CockpitContextValue);
}

beforeEach(() => {
  vi.restoreAllMocks();
  (api.vfsPut as ReturnType<typeof vi.fn>).mockClear();
});

describe("FileTree 트리 빌드/평탄화", () => {
  it("buildTree는 runId 접두를 제거하고 key를 누적경로로 부여", () => {
    const root = buildTree(NODES, RUN);
    expect(allDirKeys(root)).toEqual(
      expect.arrayContaining(["brainstorming", "design", "design/rough", "design/final", "design/final/ko"]),
    );
  });
  it("flattenTree는 펼친 디렉터리의 자식을 순서대로 노출", () => {
    const root = buildTree(NODES.filter((n: any) => !n.path.includes("_state") && !n.path.includes("usage")), RUN);
    const rows = flattenTree(root, new Set(), "");
    const names = rows.map((r) => r.name);
    expect(names).toContain("spec.md");
    expect(names).toContain("layout.spec.json");
  });
});

describe("FileTree 렌더", () => {
  it("내부(_)·usage 노드는 숨기고 카운트에 미포함", () => {
    mockCockpit();
    render(<FileTree />);
    expect(screen.queryByText("_state.json")).toBeNull();
    expect(screen.queryByText("log.jsonl")).toBeNull();
  });
  it("파일타입 배지를 표시(.md=MD, .json={})", () => {
    mockCockpit();
    render(<FileTree />);
    const mdRow = screen.getByTestId("file-spec.md");
    expect(within(mdRow).getByText("MD")).toBeTruthy();
  });
  it("디렉터리 클릭 시 접힌다(자식 숨김)", () => {
    mockCockpit();
    render(<FileTree />);
    expect(screen.getByTestId("file-spec.md")).toBeTruthy();
    fireEvent.click(screen.getByRole("treeitem", { name: /brainstorming/ }));
    expect(screen.queryByTestId("file-spec.md")).toBeNull();
  });
  it("파일 클릭 시 selectFile(전체경로)", () => {
    const selectFile = vi.fn();
    mockCockpit({ selectFile });
    render(<FileTree />);
    fireEvent.click(screen.getByTestId("file-spec.md"));
    expect(selectFile).toHaveBeenCalledWith("/run1/brainstorming/spec.md");
  });
});

describe("FileTree 전체 펼치기/접기", () => {
  it("전체 접기 → 최상위만 남고 자식 숨김, 전체 펼치기 → 다시 노출", () => {
    mockCockpit();
    render(<FileTree />);
    expect(screen.getByTestId("file-spec.md")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "전체 접기" }));
    expect(screen.queryByTestId("file-spec.md")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "전체 펼치기" }));
    expect(screen.getByTestId("file-spec.md")).toBeTruthy();
  });
});

describe("FileTree 경로 복사", () => {
  it("복사 버튼 클릭 → clipboard에 VFS 경로", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    mockCockpit();
    render(<FileTree />);
    const row = screen.getByTestId("file-spec.md");
    fireEvent.click(within(row).getByLabelText("경로 복사"));
    expect(writeText).toHaveBeenCalledWith("/run1/brainstorming/spec.md");
  });
});

describe("FileTree 검색", () => {
  it("검색어 입력 시 매치 파일만 남는다", () => {
    mockCockpit();
    render(<FileTree />);
    fireEvent.change(screen.getByPlaceholderText("파일 검색…"), { target: { value: "scene" } });
    expect(screen.getByTestId("file-main.scene")).toBeTruthy();
    expect(screen.queryByTestId("file-spec.md")).toBeNull();
  });
  it("매치 0건이면 안내 문구", () => {
    mockCockpit();
    render(<FileTree />);
    fireEvent.change(screen.getByPlaceholderText("파일 검색…"), { target: { value: "zzz없음" } });
    expect(screen.getByText("검색 결과가 없습니다")).toBeTruthy();
  });
});

describe("FileTree 키보드 내비", () => {
  it("ArrowDown→Enter로 첫 행(brainstorming) 토글", () => {
    mockCockpit();
    render(<FileTree />);
    const tree = screen.getByRole("tree");
    fireEvent.keyDown(tree, { key: "ArrowDown" }); // index 0 활성(brainstorming dir)
    expect(screen.getByTestId("file-spec.md")).toBeTruthy();
    fireEvent.keyDown(tree, { key: "ArrowLeft" }); // dir 접기
    expect(screen.queryByTestId("file-spec.md")).toBeNull();
  });
  it("파일 행에서 Enter → selectFile", () => {
    const selectFile = vi.fn();
    mockCockpit({ selectFile });
    render(<FileTree />);
    const tree = screen.getByRole("tree");
    // 0:brainstorming(dir) → 1:spec.md(file)
    fireEvent.keyDown(tree, { key: "ArrowDown" });
    fireEvent.keyDown(tree, { key: "ArrowDown" });
    fireEvent.keyDown(tree, { key: "Enter" });
    expect(selectFile).toHaveBeenCalledWith("/run1/brainstorming/spec.md");
  });
});

describe("FileTree 업로드", () => {
  it("소비 스튜디오(review)에서 업로드 버튼 노출·vfsPut·refreshTree 호출", async () => {
    const refreshTree = vi.fn().mockResolvedValue(undefined);
    mockCockpit({ activeStudio: "review", refreshTree } as any);
    render(<FileTree />);
    const input = screen.getByTestId("upload-input") as HTMLInputElement;
    const file = new File(["자료 본문"], "note.md", { type: "text/markdown" });
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => expect(api.vfsPut).toHaveBeenCalledWith(
      "run1", "review/uploads/note.md", "자료 본문", "text/markdown", undefined));
    expect(refreshTree).toHaveBeenCalled();
  });
  it("비소비 스튜디오(deploy)에선 업로드 버튼 숨김", () => {
    mockCockpit({ activeStudio: "deploy" } as any);
    render(<FileTree />);
    expect(screen.queryByTestId("upload-file")).toBeNull();
  });
  it("허용 외 확장자는 에러 캡션 표시·vfsPut 미호출", async () => {
    mockCockpit({ activeStudio: "review", refreshTree: vi.fn() } as any);
    render(<FileTree />);
    const input = screen.getByTestId("upload-input") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [new File(["x"], "evil.exe")] } });
    await screen.findByText(/업로드할 수 있어요/);
    expect(api.vfsPut).not.toHaveBeenCalled();
  });
});
