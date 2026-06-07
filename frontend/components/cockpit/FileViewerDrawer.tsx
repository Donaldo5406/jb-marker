"use client";

import * as React from "react";
import { Copy, Save, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { fileType, displayName, baseName } from "@/lib/fileType";
import { filePlacement } from "@/lib/cockpit-nav";
import { FileContent } from "./FileContent";
import { useCockpit } from "./CockpitProvider";

/** 우측 와이드 드로어 — design/review/deploy의 트리 파일 인스펙션 표면.
 *  filePlacement === 'drawer'일 때만 마운트. Esc/백드롭으로 닫힘. */
export function FileViewerDrawer() {
  const c = useCockpit();
  const file = c.openFile;
  const [saving, setSaving] = React.useState(false);
  const open = !!file && filePlacement(c.activeStudio, file.path) === "drawer";

  React.useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") c.closeFile();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, c]);

  if (!open || !file) return null;

  const isScene = file.path.endsWith(".scene");
  const isText = !isScene && !/\.(png|jpe?g|gif|webp|avif|bmp|ico)$/i.test(file.path);
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
    <div className="fixed inset-0 z-40" data-testid="file-viewer-drawer">
      <div className="absolute inset-0 bg-black/30" data-testid="drawer-backdrop" onClick={c.closeFile} aria-hidden />
      <div
        role="dialog"
        aria-label="파일 뷰어"
        className="absolute right-0 top-0 flex h-full w-[min(640px,90vw)] flex-col bg-surface shadow-ambient animate-fade-in-up"
      >
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
            {file.dirty && <span className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-label="저장되지 않은 변경" />}
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
    </div>
  );
}
