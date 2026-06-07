"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import { Code2, Eye } from "lucide-react";
import { cn } from "@/lib/utils";
import { isImagePath, baseName } from "@/lib/fileType";
import { ImageView } from "./ImageView";
import type { OpenFile } from "./CockpitProvider";

const FabricEditor = dynamic(() => import("./FabricEditor").then((m) => m.FabricEditor), { ssr: false });
const MarkdownView = dynamic(() => import("./MarkdownView").then((m) => m.MarkdownView), {
  loading: () => <div className="flex-1 bg-surface" />,
});
const CodeView = dynamic(() => import("./CodeView").then((m) => m.CodeView), {
  loading: () => <div className="flex-1 bg-surface" />,
});

function parseScene(content: string): { objects: any[] } | null {
  if (!content) return null;
  try {
    return JSON.parse(content) as { objects: any[] };
  } catch {
    return null;
  }
}

/** 파일 1건의 본문 렌더(확장자 분기) + md/code 보기 토글.
 *  파일 액션(저장/복사/닫기)·경로 표시는 래퍼(EditorPane / FileViewerDrawer)가 담당. */
export function FileContent({
  file,
  runId,
  onChangeContent,
  onSaveScene,
}: {
  file: OpenFile;
  runId: string | null;
  onChangeContent: (text: string) => void;
  onSaveScene: (json: string) => void | Promise<void>;
}) {
  const [mdMode, setMdMode] = React.useState<"preview" | "source">("preview");
  const [codeMode, setCodeMode] = React.useState<"read" | "source">("read");
  React.useEffect(() => {
    setMdMode("preview");
    setCodeMode("read");
  }, [file.path]);

  const isScene = file.path.endsWith(".scene");
  const isMd = file.path.endsWith(".md");
  const isImage = isImagePath(file.path);
  const isCode = !isScene && !isMd && !isImage;
  const showPreview = isMd && mdMode === "preview";
  const showCodeRead = isCode && codeMode === "read";

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-surface">
      {(isMd || isCode) && (
        <div className="flex items-center justify-end border-b border-outline-variant bg-surface-container-low px-3 py-1.5">
          <button
            type="button"
            onClick={() =>
              isMd
                ? setMdMode((m) => (m === "preview" ? "source" : "preview"))
                : setCodeMode((m) => (m === "read" ? "source" : "read"))
            }
            aria-label={isMd ? (showPreview ? "소스 보기" : "미리보기") : showCodeRead ? "소스 보기" : "읽기"}
            title={isMd ? (showPreview ? "소스 보기" : "미리보기") : showCodeRead ? "소스 보기" : "읽기"}
            className="inline-flex items-center gap-1.5 rounded-full border border-outline-variant px-3 py-1 text-caption font-medium text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface"
          >
            {showPreview || showCodeRead ? <Code2 className="h-3.5 w-3.5" aria-hidden /> : <Eye className="h-3.5 w-3.5" aria-hidden />}
            {isMd ? (showPreview ? "소스" : "미리보기") : showCodeRead ? "소스" : "읽기"}
          </button>
        </div>
      )}
      {isScene ? (
        <FabricEditor scene={parseScene(file.content)} onSave={(json) => onSaveScene(JSON.stringify(json))} />
      ) : isImage ? (
        <ImageView runId={runId} path={file.path} />
      ) : showPreview ? (
        <MarkdownView content={file.content} />
      ) : showCodeRead ? (
        <CodeView name={baseName(file.path)} content={file.content} />
      ) : (
        <textarea
          value={file.content}
          onChange={(e) => onChangeContent(e.target.value)}
          spellCheck={false}
          className={cn(
            "flex-1 resize-none bg-surface px-5 py-4 font-mono text-body-sm leading-relaxed text-on-surface outline-none placeholder:text-outline",
          )}
          placeholder="내용이 비어 있습니다…"
        />
      )}
    </div>
  );
}
