"use client";

import * as React from "react";
import { Copy, ImageIcon, Loader2, Save, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { fileType, displayName } from "@/lib/fileType";
import { FileContent } from "./FileContent";
import { useCockpit } from "./CockpitProvider";

function baseName(path: string): string {
  const segs = path.split("/").filter(Boolean);
  return segs[segs.length - 1] ?? path;
}

/** brainstorming 중앙 인라인 표면: 파일 액션 툴바 + FileContent. */
export function EditorPane() {
  const c = useCockpit();
  const file = c.openFile;
  const [saving, setSaving] = React.useState(false);

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
  const isText = !isScene && !file.path.match(/\.(png|jpe?g|gif|webp|avif|bmp|ico)$/i);
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
      <div className="flex items-center gap-2 border-b border-outline-variant bg-surface-container-low px-3 py-2">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          {!isScene && (
            <span className={cn("flex h-4 w-4 shrink-0 items-center justify-center rounded text-[8px] font-bold leading-none", ft.fg, ft.bg)} aria-hidden>
              {ft.label}
            </span>
          )}
          <span className="truncate text-body-sm font-medium text-on-surface" title={file.path}>
            {displayName(baseName(file.path))}
          </span>
          {file.dirty && (
            <span className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-label="저장되지 않은 변경" title="저장되지 않은 변경" />
          )}
        </div>
        {isText && (
          <button type="button" onClick={() => void navigator.clipboard?.writeText(file.content)} aria-label="내용 복사" title="내용 복사"
            className="inline-flex h-7 w-7 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface">
            <Copy className="h-3.5 w-3.5" aria-hidden />
          </button>
        )}
        {isText && (
          <button type="button" onClick={handleSave} disabled={!file.dirty || saving}
            className={cn("inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-caption font-medium transition-colors", "disabled:opacity-40 disabled:pointer-events-none", "bg-primary text-on-primary hover:bg-primary-container")}>
            <Save className="h-3.5 w-3.5" aria-hidden />
            {saving ? "저장 중…" : "저장"}
          </button>
        )}
        <button type="button" onClick={c.closeFile} aria-label="파일 닫기" title="닫기"
          className="inline-flex h-7 w-7 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface">
          <X className="h-4 w-4" aria-hidden />
        </button>
      </div>
      <FileContent file={file} runId={c.runId} onChangeContent={c.setOpenFileContent} onSaveScene={c.saveSceneJson} />
    </div>
  );
}
