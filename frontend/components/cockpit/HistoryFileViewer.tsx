"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import { X } from "lucide-react";
import { api } from "@/lib/api";
import { baseName, displayName, fileType } from "@/lib/fileType";
import { cn } from "@/lib/utils";

const MarkdownView = dynamic(() => import("./MarkdownView").then((m) => m.MarkdownView), {
  loading: () => <div className="flex-1 bg-surface" />,
});
const CodeView = dynamic(() => import("./CodeView").then((m) => m.CodeView), {
  loading: () => <div className="flex-1 bg-surface" />,
});

type LoadState = "loading" | "ok" | "error";

/** History 상세 전용 문서 뷰어 — plan.md·spec.md·*.json 등 텍스트 산출물을 우측 드로어로
 *  인스펙션한다. 워크스페이스 컨텍스트(openFile/activeStudio)와 분리돼, 지금 보고 있는
 *  run(runId)의 파일만 vfsGet으로 직접 로드한다(다른 run 오염 방지). Esc/백드롭으로 닫힘. */
export function HistoryFileViewer({
  runId,
  path,
  onClose,
}: {
  runId: string;
  path: string;
  onClose: () => void;
}) {
  const [content, setContent] = React.useState<string>("");
  const [state, setState] = React.useState<LoadState>("loading");

  React.useEffect(() => {
    let cancelled = false;
    setState("loading");
    const prefix = `/${runId}/`;
    const rest = path.startsWith(prefix) ? path.slice(prefix.length) : path.replace(/^\//, "");
    api
      .vfsGet(runId, rest)
      .then((n) => {
        if (!cancelled) {
          setContent(n.content_text ?? "");
          setState("ok");
        }
      })
      .catch(() => {
        if (!cancelled) setState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [runId, path]);

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const name = baseName(path);
  const isMd = path.endsWith(".md");
  const ft = fileType(name);

  return (
    <div className="fixed inset-0 z-40" data-testid="history-file-viewer">
      <div className="absolute inset-0 bg-black/30" data-testid="history-file-backdrop" onClick={onClose} aria-hidden />
      <div
        role="dialog"
        aria-label="파일 뷰어"
        className="absolute right-0 top-0 flex h-full w-[min(640px,90vw)] flex-col bg-surface shadow-ambient animate-fade-in-up"
      >
        <div className="flex items-center gap-2 border-b border-outline-variant bg-surface-container-low px-3 py-2">
          <span
            className={cn(
              "flex h-4 w-4 shrink-0 items-center justify-center rounded text-[8px] font-bold leading-none",
              ft.fg,
              ft.bg,
            )}
            aria-hidden
          >
            {ft.label}
          </span>
          <span className="truncate text-body-sm font-medium text-on-surface" title={path}>
            {displayName(name)}
          </span>
          <button
            type="button"
            onClick={onClose}
            aria-label="파일 닫기"
            title="닫기"
            className="ml-auto inline-flex h-7 w-7 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>
        {state === "loading" ? (
          <div className="flex-1 animate-pulse bg-surface-container-high" />
        ) : state === "error" ? (
          <div className="flex flex-1 items-center justify-center text-body-sm text-on-surface-variant">
            파일을 불러오지 못했습니다.
          </div>
        ) : isMd ? (
          <MarkdownView content={content} />
        ) : (
          <CodeView name={name} content={content} />
        )}
      </div>
    </div>
  );
}
