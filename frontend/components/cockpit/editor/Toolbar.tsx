// frontend/components/cockpit/editor/Toolbar.tsx
"use client";
import * as React from "react";
import { Undo2, Redo2, ZoomIn, ZoomOut, Maximize, Save, X } from "lucide-react";
import { cn } from "@/lib/utils";

export function Toolbar({
  canUndo, canRedo, zoom, saving, dirty,
  onUndo, onRedo, onZoomIn, onZoomOut, onZoomFit, onSave, onClose,
}: {
  canUndo: boolean; canRedo: boolean; zoom: number; saving: boolean; dirty: boolean;
  onUndo: () => void; onRedo: () => void; onZoomIn: () => void; onZoomOut: () => void;
  onZoomFit: () => void; onSave: () => void; onClose: () => void;
}) {
  const icon = "inline-flex h-7 w-7 items-center justify-center rounded-full text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface disabled:opacity-40 disabled:pointer-events-none";
  return (
    <div className="flex items-center gap-1.5 border-t border-outline-variant bg-surface px-3 py-2">
      <button type="button" aria-label="실행 취소" className={icon} disabled={!canUndo} onClick={onUndo}><Undo2 className="h-4 w-4" /></button>
      <button type="button" aria-label="다시 실행" className={icon} disabled={!canRedo} onClick={onRedo}><Redo2 className="h-4 w-4" /></button>
      <span className="mx-1 h-4 w-px bg-outline-variant" />
      <button type="button" aria-label="축소" className={icon} onClick={onZoomOut}><ZoomOut className="h-4 w-4" /></button>
      <span className="min-w-[3rem] text-center text-caption text-on-surface-variant">{Math.round(zoom * 100)}%</span>
      <button type="button" aria-label="확대" className={icon} onClick={onZoomIn}><ZoomIn className="h-4 w-4" /></button>
      <button type="button" aria-label="화면 맞춤" className={icon} onClick={onZoomFit}><Maximize className="h-4 w-4" /></button>
      <button type="button" aria-label="닫기" className={cn(icon, "ml-auto")} onClick={onClose}><X className="h-4 w-4" /></button>
      <button type="button" onClick={onSave} disabled={saving || !dirty}
        className="inline-flex items-center gap-1.5 rounded-full bg-primary px-3 py-1.5 text-caption font-medium text-on-primary hover:bg-primary-container disabled:opacity-40 disabled:pointer-events-none">
        <Save className="h-3.5 w-3.5" />{saving ? "저장 중…" : "scene 저장"}
      </button>
    </div>
  );
}
