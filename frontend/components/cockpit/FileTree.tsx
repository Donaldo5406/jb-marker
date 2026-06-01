"use client";

import * as React from "react";
import { ChevronRight, Folder, FolderOpen, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useCockpit } from "./CockpitProvider";
import { fileType } from "@/lib/fileType";
import type { VfsNode } from "@/lib/api";

type TreeNode = {
  name: string;
  key: string;             // runId 제거 후 누적 경로(예: "design/rough")
  fullPath: string | null; // 파일만 — selectFile 전달용 전체 VFS 경로
  isDir: boolean;
  children: Map<string, TreeNode>;
};

export type Row = {
  key: string; name: string; depth: number; isDir: boolean;
  fullPath: string | null; expanded: boolean; hasChildren: boolean;
};

function newNode(name: string, key: string, isDir: boolean): TreeNode {
  return { name, key, fullPath: null, isDir, children: new Map() };
}

export function buildTree(nodes: VfsNode[], runId: string): TreeNode {
  const root = newNode("", "", true);
  const prefix = `/${runId}/`;
  for (const node of nodes) {
    const rest = node.path.startsWith(prefix) ? node.path.slice(prefix.length) : node.path.replace(/^\/+/, "");
    if (!rest) continue;
    const segments = rest.split("/").filter(Boolean);
    let cursor = root;
    segments.forEach((seg, idx) => {
      const isLeaf = idx === segments.length - 1;
      const key = segments.slice(0, idx + 1).join("/");
      let child = cursor.children.get(seg);
      if (!child) { child = newNode(seg, key, !isLeaf); cursor.children.set(seg, child); }
      if (isLeaf) { child.isDir = false; child.fullPath = node.path; }
      cursor = child;
    });
  }
  return root;
}

function sortedChildren(node: TreeNode): TreeNode[] {
  return [...node.children.values()].sort((a, b) => {
    if (a.isDir !== b.isDir) return a.isDir ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
}

export function allDirKeys(root: TreeNode): string[] {
  const keys: string[] = [];
  const walk = (n: TreeNode) => {
    for (const c of n.children.values()) if (c.isDir) { keys.push(c.key); walk(c); }
  };
  walk(root);
  return keys;
}

/** collapsed 집합과 검색어를 적용해 가시 행을 평탄화. 검색 중엔 매치 경로를 자동 펼침. */
export function flattenTree(root: TreeNode, collapsed: Set<string>, query: string): Row[] {
  const q = query.trim().toLowerCase();
  const matches = (node: TreeNode): boolean => {
    if (!node.isDir) return node.key.toLowerCase().includes(q);
    for (const c of node.children.values()) if (matches(c)) return true;
    return false;
  };
  const rows: Row[] = [];
  const walk = (node: TreeNode, depth: number) => {
    for (const child of sortedChildren(node)) {
      if (q && !matches(child)) continue;
      const hasChildren = child.children.size > 0;
      const expanded = child.isDir && (q ? true : !collapsed.has(child.key));
      rows.push({
        key: child.key, name: child.name, depth, isDir: child.isDir,
        fullPath: child.fullPath, expanded, hasChildren,
      });
      if (child.isDir && expanded) walk(child, depth + 1);
    }
  };
  walk(root, 0);
  return rows;
}

/** 좌측 패널: VFS 트리(평탄화 렌더). */
export function FileTree() {
  const c = useCockpit();
  const [query, setQuery] = React.useState("");
  const [collapsed, setCollapsed] = React.useState<Set<string>>(() => new Set());

  // 숨김: 내부 상태(_접두) + 관측성(usage). 비용/토큰은 History에서 제공.
  const visible = React.useMemo(
    () => c.nodes.filter((n) => {
      const segs = n.path.split("/");
      return !segs.some((seg) => seg.startsWith("_") || seg === "usage");
    }),
    [c.nodes],
  );
  const tree = React.useMemo(
    () => (c.runId ? buildTree(visible, c.runId) : newNode("", "", true)),
    [visible, c.runId],
  );
  const rows = React.useMemo(() => flattenTree(tree, collapsed, query), [tree, collapsed, query]);

  const toggleDir = React.useCallback((key: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  }, []);
  const expandAll = React.useCallback(() => setCollapsed(new Set()), []);
  const collapseAll = React.useCallback(
    () => setCollapsed(new Set(allDirKeys(tree))),
    [tree],
  );

  const [activeIndex, setActiveIndex] = React.useState(-1);
  React.useEffect(() => {
    setActiveIndex((i) => Math.min(i, rows.length - 1));
  }, [rows.length]);

  const onKeyDown = React.useCallback((e: React.KeyboardEvent) => {
    if (rows.length === 0) return;
    const row = rows[Math.max(0, Math.min(activeIndex, rows.length - 1))];
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(rows.length - 1, i + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(0, i - 1));
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      if (row.isDir && !row.expanded) toggleDir(row.key);
      else setActiveIndex((i) => Math.min(rows.length - 1, i + 1));
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      if (row.isDir && row.expanded) toggleDir(row.key);
      else setActiveIndex((i) => Math.max(0, i - 1));
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (row.isDir) toggleDir(row.key);
      else if (row.fullPath) void c.selectFile(row.fullPath);
    }
  }, [rows, activeIndex, toggleDir, c]);

  return (
    <div className="flex h-full flex-col overflow-hidden bg-surface-container-low">
      <div className="flex items-center justify-between border-b border-outline-variant px-3 py-2">
        <span className="text-caption uppercase tracking-wide text-on-surface-variant">탐색기</span>
        <span className="flex items-center gap-1.5">
          <span className="text-caption text-outline">{visible.length}</span>
          <button type="button" aria-label="전체 펼치기" title="전체 펼치기" onClick={expandAll}
            className="rounded border border-outline-variant px-1.5 py-0.5 text-[11px] text-on-surface-variant hover:bg-surface-container-high">⤢</button>
          <button type="button" aria-label="전체 접기" title="전체 접기" onClick={collapseAll}
            className="rounded border border-outline-variant px-1.5 py-0.5 text-[11px] text-on-surface-variant hover:bg-surface-container-high">⤡</button>
        </span>
      </div>
      <div className="border-b border-outline-variant p-2">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="파일 검색…"
          aria-label="파일 검색"
          className="w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-2.5 py-1.5 text-body-sm text-on-surface outline-none placeholder:text-outline focus:border-on-surface-variant"
        />
      </div>
      <div className="flex-1 overflow-y-auto p-2" role="tree" aria-label="산출물 트리"
        tabIndex={0} onKeyDown={onKeyDown}>
        {rows.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 px-4 text-center">
            <Folder className="h-8 w-8 text-outline-variant" aria-hidden />
            {query.trim() ? (
              <p className="text-body-sm text-on-surface-variant">검색 결과가 없습니다</p>
            ) : (
              <>
                <p className="text-body-sm text-on-surface-variant">아직 산출물이 없습니다</p>
                <p className="text-caption text-outline">우측 챗으로 작업을 시작하면 트리에 나타납니다</p>
              </>
            )}
          </div>
        ) : (
          rows.map((row, i) => (
            <TreeRow key={row.key} row={row} active={i === activeIndex} onToggle={toggleDir} />
          ))
        )}
      </div>
    </div>
  );
}

function TreeRow({ row, active, onToggle }: { row: Row; active: boolean; onToggle: (key: string) => void }) {
  const c = useCockpit();
  const loading = c.loadingPath === row.fullPath;
  const selected = c.openFile?.path === row.fullPath || loading;
  const indent = { paddingLeft: 8 + row.depth * 14 } as React.CSSProperties;
  // 키보드 활성 행에 ring 표시(roving)
  const ring = active ? "ring-1 ring-inset ring-outline" : "";

  if (row.isDir) {
    return (
      <button
        type="button"
        role="treeitem"
        aria-level={row.depth + 1}
        aria-expanded={row.expanded}
        onClick={() => onToggle(row.key)}
        style={indent}
        className={cn("flex w-full items-center gap-1 rounded-md py-1 pr-2 text-left text-body-sm font-medium text-on-surface-variant transition-colors hover:bg-surface-container-high", ring)}
      >
        <ChevronRight className={cn("h-3.5 w-3.5 shrink-0 text-outline transition-transform", row.expanded && "rotate-90")} aria-hidden />
        {row.expanded ? <FolderOpen className="h-3.5 w-3.5 shrink-0 text-outline" aria-hidden /> : <Folder className="h-3.5 w-3.5 shrink-0 text-outline" aria-hidden />}
        <span className="truncate">{row.name}</span>
      </button>
    );
  }

  const { label, fg, bg } = fileType(row.name);
  return (
    <button
      type="button"
      role="treeitem"
      aria-level={row.depth + 1}
      aria-selected={selected}
      onClick={() => row.fullPath && void c.selectFile(row.fullPath)}
      title={row.name}
      data-testid={`file-${row.name}`}
      aria-busy={loading || undefined}
      style={indent}
      className={cn(
        "group flex w-full items-center gap-1.5 rounded-md py-1 pr-2 text-left text-body-sm transition-colors",
        selected
          ? "bg-surface-container-highest font-medium text-on-surface"
          : "text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface",
        ring,
      )}
    >
      {loading ? (
        <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-primary" aria-hidden />
      ) : (
        <span className={cn("flex h-4 w-4 shrink-0 items-center justify-center rounded text-[8px] font-bold leading-none", fg, bg)} aria-hidden>
          {label}
        </span>
      )}
      <span className="truncate">{row.name}</span>
      {row.fullPath && (
        <span
          role="button"
          tabIndex={-1}
          aria-label="경로 복사"
          title="경로 복사"
          onClick={(e) => { e.stopPropagation(); void navigator.clipboard?.writeText(row.fullPath!); }}
          className="ml-auto hidden shrink-0 rounded px-1 text-[11px] text-outline hover:text-on-surface group-hover:inline"
        >⧉</span>
      )}
    </button>
  );
}
