// frontend/components/cockpit/editor/Toolbar.tsx
"use client";
import * as React from "react";
import {
  Undo2, Redo2, ZoomIn, ZoomOut, Maximize, Save, X,
  Type, Square, Circle as CircleIcon, Minus, ImagePlus,
  AlignStartVertical, AlignCenterVertical, AlignEndVertical,
  AlignStartHorizontal, AlignCenterHorizontal, AlignEndHorizontal,
  AlignHorizontalDistributeCenter, AlignVerticalDistributeCenter,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { AlignMode } from "@/lib/editor/align";

export function Toolbar({
  canUndo, canRedo, zoom, saving, dirty, canAlign,
  onUndo, onRedo, onZoomIn, onZoomOut, onZoomFit, onSave, onClose,
  onAddText, onAddRect, onAddCircle, onAddLine, onImportImage, onAlign, onDistribute,
}: {
  canUndo: boolean; canRedo: boolean; zoom: number; saving: boolean; dirty: boolean; canAlign: boolean;
  onUndo: () => void; onRedo: () => void; onZoomIn: () => void; onZoomOut: () => void;
  onZoomFit: () => void; onSave: () => void; onClose: () => void;
  onAddText: () => void; onAddRect: () => void; onAddCircle: () => void; onAddLine: () => void;
  onImportImage: () => void; onAlign: (mode: AlignMode) => void; onDistribute: (axis: "h" | "v") => void;
}) {
  const icon = "inline-flex h-7 w-7 items-center justify-center rounded-full text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface disabled:opacity-40 disabled:pointer-events-none";
  const sep = <span className="mx-1 h-4 w-px bg-outline-variant" />;
  return (
    <div className="flex flex-wrap items-center gap-1.5 border-t border-outline-variant bg-surface px-3 py-2">
      {/* 삽입 도구 */}
      <button type="button" aria-label="텍스트 추가" className={icon} onClick={onAddText}><Type className="h-4 w-4" /></button>
      <button type="button" aria-label="사각형 추가" className={icon} onClick={onAddRect}><Square className="h-4 w-4" /></button>
      <button type="button" aria-label="원 추가" className={icon} onClick={onAddCircle}><CircleIcon className="h-4 w-4" /></button>
      <button type="button" aria-label="선 추가" className={icon} onClick={onAddLine}><Minus className="h-4 w-4" /></button>
      <button type="button" aria-label="이미지 가져오기" className={icon} onClick={onImportImage}><ImagePlus className="h-4 w-4" /></button>
      {sep}
      {/* 정렬(선택 있을 때만) */}
      {canAlign && (
        <>
          <button type="button" aria-label="왼쪽 정렬" className={icon} onClick={() => onAlign("left")}><AlignStartVertical className="h-4 w-4" /></button>
          <button type="button" aria-label="가로 가운데 정렬" className={icon} onClick={() => onAlign("hcenter")}><AlignCenterVertical className="h-4 w-4" /></button>
          <button type="button" aria-label="오른쪽 정렬" className={icon} onClick={() => onAlign("right")}><AlignEndVertical className="h-4 w-4" /></button>
          <button type="button" aria-label="위쪽 정렬" className={icon} onClick={() => onAlign("top")}><AlignStartHorizontal className="h-4 w-4" /></button>
          <button type="button" aria-label="세로 가운데 정렬" className={icon} onClick={() => onAlign("vcenter")}><AlignCenterHorizontal className="h-4 w-4" /></button>
          <button type="button" aria-label="아래쪽 정렬" className={icon} onClick={() => onAlign("bottom")}><AlignEndHorizontal className="h-4 w-4" /></button>
          <button type="button" aria-label="가로 균등 분배" className={icon} onClick={() => onDistribute("h")}><AlignHorizontalDistributeCenter className="h-4 w-4" /></button>
          <button type="button" aria-label="세로 균등 분배" className={icon} onClick={() => onDistribute("v")}><AlignVerticalDistributeCenter className="h-4 w-4" /></button>
          {sep}
        </>
      )}
      {/* 히스토리/줌 */}
      <button type="button" aria-label="실행 취소" className={icon} disabled={!canUndo} onClick={onUndo}><Undo2 className="h-4 w-4" /></button>
      <button type="button" aria-label="다시 실행" className={icon} disabled={!canRedo} onClick={onRedo}><Redo2 className="h-4 w-4" /></button>
      {sep}
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
