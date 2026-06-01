"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import { Code2, Copy, Eye, ImageIcon, Loader2, Save, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { fileType } from "@/lib/fileType";
import { useCockpit } from "./CockpitProvider";

/** FabricEditor는 client-only(브라우저 canvas 의존) — SSR 비활성 lazy-load. */
const FabricEditor = dynamic(
  () => import("./FabricEditor").then((m) => m.FabricEditor),
  { ssr: false },
);

/** MarkdownView는 react-markdown 번들(~46KB)을 끌어오므로 .md Preview를 열 때만 lazy-load. */
const MarkdownView = dynamic(
  () => import("./MarkdownView").then((m) => m.MarkdownView),
  { loading: () => <div className="flex-1 bg-surface" /> },
);

/** CodeView는 highlight.js 번들을 끌어오므로 코드 파일을 READ로 열 때만 lazy-load. */
const CodeView = dynamic(
  () => import("./CodeView").then((m) => m.CodeView),
  { loading: () => <div className="flex-1 bg-surface" /> },
);

/** 파일명에서 마지막 세그먼트만(상단 바 표시용). */
function baseName(path: string): string {
  const segs = path.split("/").filter(Boolean);
  return segs[segs.length - 1] ?? path;
}

/** scene 파일 내용을 안전 파싱 — 잘못된 JSON이어도 렌더 크래시 없이 null 반환. */
function parseScene(content: string): { objects: any[] } | null {
  if (!content) return null;
  try {
    return JSON.parse(content) as { objects: any[] };
  } catch {
    return null;
  }
}

/** 중앙 패널: 파일 뷰어/에디터. 확장자별 렌더러 분기(C3 이중성).
 *  - openFile===null : 빈 상태
 *  - .scene          : IMG.LY placeholder (Deferral D2)
 *  - .md/.json/그외  : textarea 텍스트 에디터(편집·저장·닫기) */
export function EditorPane() {
  const c = useCockpit();
  const file = c.openFile;
  const [saving, setSaving] = React.useState(false);
  // .md 보기 모드(Preview=렌더, Source=raw 편집). 파일이 바뀌면 Preview로 초기화(기본 = 보기쉽게).
  const [mdMode, setMdMode] = React.useState<"preview" | "source">("preview");
  // 코드 파일(.json/.ts 등) 보기 모드(read=강조 읽기, source=raw 편집). 파일이 바뀌면 read로 초기화.
  const [codeMode, setCodeMode] = React.useState<"read" | "source">("read");
  const filePath = file?.path;
  React.useEffect(() => {
    setMdMode("preview");
    setCodeMode("read");
  }, [filePath]);

  // 캐시 미스로 fetch 중이고 아직 해당 파일이 안 열렸으면 로딩 표시(체감 지연 완화).
  const loadingNew = c.loadingPath && (!file || file.path !== c.loadingPath);
  if (loadingNew) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 bg-surface px-8 text-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" aria-hidden />
        <p className="text-body-sm text-on-surface-variant">불러오는 중…</p>
      </div>
    );
  }

  if (!file) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 bg-surface px-8 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-outline-variant bg-surface-container-lowest">
          <ImageIcon className="h-5 w-5 text-outline" aria-hidden />
        </div>
        <p className="text-body-lg font-medium text-on-surface">열린 파일이 없습니다</p>
        <p className="max-w-sm text-body-sm text-on-surface-variant">
          좌측 트리에서 파일을 선택하거나, 우측 챗으로 작업을 시작하세요
        </p>
      </div>
    );
  }

  const isScene = file.path.endsWith(".scene");
  const isMd = file.path.endsWith(".md");
  const isCode = !isScene && !isMd; // .json/.ts 등
  const showPreview = isMd && mdMode === "preview";
  const showCodeRead = isCode && codeMode === "read";
  const ft = fileType(baseName(file.path));

  const handleSave = async () => {
    setSaving(true);
    try {
      await c.saveFile();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden bg-surface">
      {/* 상단 바: 경로 + dirty 표시 + 저장/닫기 */}
      <div className="flex items-center gap-2 border-b border-outline-variant bg-surface-container-low px-3 py-2">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          {!isScene && (
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
          )}
          <span className="truncate text-body-sm font-medium text-on-surface" title={file.path}>
            {baseName(file.path)}
          </span>
          {file.dirty && (
            <span
              className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-primary"
              aria-label="저장되지 않은 변경"
              title="저장되지 않은 변경"
            />
          )}
        </div>
        {isMd && (
          <button
            type="button"
            onClick={() => setMdMode((m) => (m === "preview" ? "source" : "preview"))}
            aria-label={showPreview ? "소스 보기" : "미리보기"}
            title={showPreview ? "소스 보기" : "미리보기"}
            className="inline-flex items-center gap-1.5 rounded-full border border-outline-variant px-3 py-1.5 text-caption font-medium text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface"
          >
            {showPreview ? <Code2 className="h-3.5 w-3.5" aria-hidden /> : <Eye className="h-3.5 w-3.5" aria-hidden />}
            {showPreview ? "소스" : "미리보기"}
          </button>
        )}
        {isCode && (
          <button
            type="button"
            onClick={() => setCodeMode((m) => (m === "read" ? "source" : "read"))}
            aria-label={showCodeRead ? "소스 보기" : "읽기"}
            title={showCodeRead ? "소스 보기" : "읽기"}
            className="inline-flex items-center gap-1.5 rounded-full border border-outline-variant px-3 py-1.5 text-caption font-medium text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface"
          >
            {showCodeRead ? <Code2 className="h-3.5 w-3.5" aria-hidden /> : <Eye className="h-3.5 w-3.5" aria-hidden />}
            {showCodeRead ? "소스" : "읽기"}
          </button>
        )}
        {!isScene && (
          <button
            type="button"
            onClick={() => void navigator.clipboard?.writeText(file.content)}
            aria-label="내용 복사"
            title="내용 복사"
            className="inline-flex h-7 w-7 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface"
          >
            <Copy className="h-3.5 w-3.5" aria-hidden />
          </button>
        )}
        {!isScene && (
          <button
            type="button"
            onClick={handleSave}
            disabled={!file.dirty || saving}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-caption font-medium transition-colors",
              "disabled:opacity-40 disabled:pointer-events-none",
              "bg-primary text-on-primary hover:bg-primary-container",
            )}
          >
            <Save className="h-3.5 w-3.5" aria-hidden />
            {saving ? "저장 중…" : "저장"}
          </button>
        )}
        <button
          type="button"
          onClick={c.closeFile}
          aria-label="파일 닫기"
          title="닫기"
          className="inline-flex h-7 w-7 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface"
        >
          <X className="h-4 w-4" aria-hidden />
        </button>
      </div>

      {/* 본문 */}
      {isScene ? (
        <FabricEditor
          scene={parseScene(file.content)}
          onSave={(json) => c.saveSceneJson(JSON.stringify(json))}
        />
      ) : showPreview ? (
        <MarkdownView content={file.content} />
      ) : showCodeRead ? (
        <CodeView name={baseName(file.path)} content={file.content} />
      ) : (
        <textarea
          value={file.content}
          onChange={(e) => c.setOpenFileContent(e.target.value)}
          spellCheck={false}
          className={cn(
            "flex-1 resize-none bg-surface px-5 py-4 font-mono text-body-sm leading-relaxed text-on-surface",
            "outline-none placeholder:text-outline",
          )}
          placeholder="내용이 비어 있습니다…"
        />
      )}
    </div>
  );
}
