"use client";

import * as React from "react";
import { ImageIcon, Save, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useCockpit } from "./CockpitProvider";

/** 파일명에서 마지막 세그먼트만(상단 바 표시용). */
function baseName(path: string): string {
  const segs = path.split("/").filter(Boolean);
  return segs[segs.length - 1] ?? path;
}

/** 중앙 패널: 파일 뷰어/에디터. 확장자별 렌더러 분기(C3 이중성).
 *  - openFile===null : 빈 상태
 *  - .scene          : IMG.LY placeholder (Deferral D2)
 *  - .md/.json/그외  : textarea 텍스트 에디터(편집·저장·닫기) */
export function EditorPane() {
  const c = useCockpit();
  const file = c.openFile;
  const [saving, setSaving] = React.useState(false);

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
        <div className="flex flex-1 flex-col items-center justify-center gap-3 px-8 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-outline-variant bg-surface-container-lowest">
            <ImageIcon className="h-5 w-5 text-outline" aria-hidden />
          </div>
          <p className="text-body-lg font-medium text-on-surface">IMG.LY 디자인 에디터</p>
          <p className="max-w-sm text-body-sm text-on-surface-variant">
            <code className="rounded bg-surface-container px-1.5 py-0.5 text-caption">.scene</code>{" "}
            파일을 여는 시각 에디터는 M4에서 제공됩니다.
          </p>
        </div>
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
