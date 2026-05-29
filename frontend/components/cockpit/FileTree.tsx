"use client";

import * as React from "react";
import { ChevronRight, File as FileIcon, Folder, FolderOpen, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useCockpit } from "./CockpitProvider";
import type { VfsNode } from "@/lib/api";

/** path 트리 노드. dir은 자식 보유, file은 원본 VfsNode 참조. */
type TreeNode = {
  name: string;
  /** 전체 VFS path(파일만 — selectFile에 그대로 전달). */
  fullPath: string | null;
  isDir: boolean;
  children: Map<string, TreeNode>;
};

function newNode(name: string, isDir: boolean): TreeNode {
  return { name, fullPath: null, isDir, children: new Map() };
}

/** nodes(VfsNode[])를 `/{runId}/` 접두 제거 후 세그먼트별 트리로 빌드. */
function buildTree(nodes: VfsNode[], runId: string): TreeNode {
  const root = newNode("", true);
  const prefix = `/${runId}/`;
  for (const node of nodes) {
    const rest = node.path.startsWith(prefix)
      ? node.path.slice(prefix.length)
      : node.path.replace(/^\/+/, "");
    if (!rest) continue;
    const segments = rest.split("/").filter(Boolean);
    let cursor = root;
    segments.forEach((seg, idx) => {
      const isLeaf = idx === segments.length - 1;
      let child = cursor.children.get(seg);
      if (!child) {
        child = newNode(seg, !isLeaf);
        cursor.children.set(seg, child);
      }
      if (isLeaf) {
        child.isDir = false;
        child.fullPath = node.path;
      }
      cursor = child;
    });
  }
  return root;
}

/** 디렉터리 먼저, 그다음 파일 — 각 그룹 내 이름 오름차순. */
function sortedChildren(node: TreeNode): TreeNode[] {
  return [...node.children.values()].sort((a, b) => {
    if (a.isDir !== b.isDir) return a.isDir ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
}

function FileRow({ node, depth }: { node: TreeNode; depth: number }) {
  const c = useCockpit();
  const loading = c.loadingPath === node.fullPath;
  // 즉각 피드백: 열린 파일이거나 현재 로딩 중인 파일이면 active 강조(클릭 직후 바로 반영).
  const active = c.openFile?.path === node.fullPath || loading;
  return (
    <button
      type="button"
      onClick={() => node.fullPath && void c.selectFile(node.fullPath)}
      title={node.name}
      data-testid={`file-${node.name}`}
      aria-busy={loading || undefined}
      style={{ paddingLeft: 8 + depth * 14 }}
      className={cn(
        "group flex w-full items-center gap-1.5 rounded-md py-1 pr-2 text-left text-body-sm transition-colors",
        active
          ? "bg-surface-container-highest font-medium text-on-surface"
          : "text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface",
      )}
    >
      {loading ? (
        <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-primary" aria-hidden />
      ) : (
        <FileIcon className="h-3.5 w-3.5 shrink-0 text-outline" aria-hidden />
      )}
      <span className="truncate">{node.name}</span>
    </button>
  );
}

function DirRow({ node, depth }: { node: TreeNode; depth: number }) {
  const [open, setOpen] = React.useState(true);
  const kids = sortedChildren(node);
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        style={{ paddingLeft: 8 + depth * 14 }}
        className="flex w-full items-center gap-1 rounded-md py-1 pr-2 text-left text-body-sm text-on-surface-variant transition-colors hover:bg-surface-container-high"
      >
        <ChevronRight
          className={cn("h-3.5 w-3.5 shrink-0 text-outline transition-transform", open && "rotate-90")}
          aria-hidden
        />
        {open ? (
          <FolderOpen className="h-3.5 w-3.5 shrink-0 text-outline" aria-hidden />
        ) : (
          <Folder className="h-3.5 w-3.5 shrink-0 text-outline" aria-hidden />
        )}
        <span className="truncate font-medium">{node.name}</span>
      </button>
      {open && (
        <div>
          {kids.map((child) =>
            child.isDir ? (
              <DirRow key={child.name} node={child} depth={depth + 1} />
            ) : (
              <FileRow key={child.name} node={child} depth={depth + 1} />
            ),
          )}
        </div>
      )}
    </div>
  );
}

/** 좌측 패널: VFS 트리. 빈 상태/스크롤 처리. */
export function FileTree() {
  const c = useCockpit();
  // 내부 상태 노드(_state.json/_messages.json 등) 숨김: path에 `_` 접두 세그먼트가 있으면 제외.
  const visible = React.useMemo(
    () => c.nodes.filter((n) => !n.path.split("/").some((seg) => seg.startsWith("_"))),
    [c.nodes],
  );
  const tree = React.useMemo(
    () => (c.runId ? buildTree(visible, c.runId) : newNode("", true)),
    [visible, c.runId],
  );
  const roots = sortedChildren(tree);

  return (
    <div className="flex h-full flex-col overflow-hidden bg-surface-container-low">
      <div className="flex items-center justify-between border-b border-outline-variant px-3 py-2">
        <span className="text-caption uppercase tracking-wide text-on-surface-variant">탐색기</span>
        <span className="text-caption text-outline">{visible.length}</span>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {roots.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 px-4 text-center">
            <Folder className="h-8 w-8 text-outline-variant" aria-hidden />
            <p className="text-body-sm text-on-surface-variant">아직 산출물이 없습니다</p>
            <p className="text-caption text-outline">우측 챗으로 작업을 시작하면 트리에 나타납니다</p>
          </div>
        ) : (
          roots.map((child) =>
            child.isDir ? (
              <DirRow key={child.name} node={child} depth={0} />
            ) : (
              <FileRow key={child.name} node={child} depth={0} />
            ),
          )
        )}
      </div>
    </div>
  );
}
