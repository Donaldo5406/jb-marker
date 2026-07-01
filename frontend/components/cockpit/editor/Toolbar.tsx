// frontend/components/cockpit/editor/Toolbar.tsx
"use client";
import * as React from "react";
import {
  Undo2, Redo2, ZoomIn, ZoomOut, Maximize, Save, Download, X,
  Type, Square, Circle as CircleIcon, Minus, ImagePlus,
  AlignStartVertical, AlignCenterVertical, AlignEndVertical,
  AlignStartHorizontal, AlignCenterHorizontal, AlignEndHorizontal,
  AlignHorizontalDistributeCenter, AlignVerticalDistributeCenter,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { AlignMode } from "@/lib/editor/align";

/** 아이콘 툴 버튼 — aria-label + title(호버 툴팁) + focus-visible 링을 한 곳에서 보장. */
function ToolBtn({
  label, onClick, disabled, className, children,
}: {
  label: string; onClick: () => void; disabled?: boolean;
  className?: string; children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "inline-flex h-7 w-7 items-center justify-center rounded-full text-on-surface-variant transition-colors",
        "hover:bg-surface-container-high hover:text-on-surface",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
        "disabled:opacity-40 disabled:pointer-events-none",
        className,
      )}
    >
      {children}
    </button>
  );
}

export function Toolbar({
  canUndo, canRedo, zoom, saving, dirty, canAlign,
  onUndo, onRedo, onZoomIn, onZoomOut, onZoomFit, onSave, onClose,
  onAddText, onAddRect, onAddCircle, onAddLine, onImportImage, onAlign, onDistribute, onExportPng,
}: {
  canUndo: boolean; canRedo: boolean; zoom: number; saving: boolean; dirty: boolean; canAlign: boolean;
  onUndo: () => void; onRedo: () => void; onZoomIn: () => void; onZoomOut: () => void;
  onZoomFit: () => void; onSave: () => void; onClose: () => void;
  onAddText: () => void; onAddRect: () => void; onAddCircle: () => void; onAddLine: () => void;
  onImportImage: () => void; onAlign: (mode: AlignMode) => void; onDistribute: (axis: "h" | "v") => void;
  onExportPng: () => void;
}) {
  const sep = <span className="mx-1 h-4 w-px bg-outline-variant" />;
  return (
    <div className="flex flex-wrap items-center gap-1.5 border-t border-outline-variant bg-surface px-3 py-2">
      {/* 삽입 도구 */}
      <ToolBtn label="텍스트 추가" onClick={onAddText}><Type className="h-4 w-4" /></ToolBtn>
      <ToolBtn label="사각형 추가" onClick={onAddRect}><Square className="h-4 w-4" /></ToolBtn>
      <ToolBtn label="원 추가" onClick={onAddCircle}><CircleIcon className="h-4 w-4" /></ToolBtn>
      <ToolBtn label="선 추가" onClick={onAddLine}><Minus className="h-4 w-4" /></ToolBtn>
      <ToolBtn label="이미지 가져오기" onClick={onImportImage}><ImagePlus className="h-4 w-4" /></ToolBtn>
      {sep}
      {/* 정렬(선택 있을 때만) */}
      {canAlign && (
        <>
          <ToolBtn label="왼쪽 정렬" onClick={() => onAlign("left")}><AlignStartVertical className="h-4 w-4" /></ToolBtn>
          <ToolBtn label="가로 가운데 정렬" onClick={() => onAlign("hcenter")}><AlignCenterVertical className="h-4 w-4" /></ToolBtn>
          <ToolBtn label="오른쪽 정렬" onClick={() => onAlign("right")}><AlignEndVertical className="h-4 w-4" /></ToolBtn>
          <ToolBtn label="위쪽 정렬" onClick={() => onAlign("top")}><AlignStartHorizontal className="h-4 w-4" /></ToolBtn>
          <ToolBtn label="세로 가운데 정렬" onClick={() => onAlign("vcenter")}><AlignCenterHorizontal className="h-4 w-4" /></ToolBtn>
          <ToolBtn label="아래쪽 정렬" onClick={() => onAlign("bottom")}><AlignEndHorizontal className="h-4 w-4" /></ToolBtn>
          <ToolBtn label="가로 균등 분배" onClick={() => onDistribute("h")}><AlignHorizontalDistributeCenter className="h-4 w-4" /></ToolBtn>
          <ToolBtn label="세로 균등 분배" onClick={() => onDistribute("v")}><AlignVerticalDistributeCenter className="h-4 w-4" /></ToolBtn>
          {sep}
        </>
      )}
      {/* 히스토리/줌 */}
      <ToolBtn label="실행 취소" disabled={!canUndo} onClick={onUndo}><Undo2 className="h-4 w-4" /></ToolBtn>
      <ToolBtn label="다시 실행" disabled={!canRedo} onClick={onRedo}><Redo2 className="h-4 w-4" /></ToolBtn>
      {sep}
      <ToolBtn label="축소" onClick={onZoomOut}><ZoomOut className="h-4 w-4" /></ToolBtn>
      <span className="min-w-[3rem] text-center text-caption text-on-surface-variant">{Math.round(zoom * 100)}%</span>
      <ToolBtn label="확대" onClick={onZoomIn}><ZoomIn className="h-4 w-4" /></ToolBtn>
      <ToolBtn label="화면 맞춤" onClick={onZoomFit}><Maximize className="h-4 w-4" /></ToolBtn>
      <ToolBtn label="닫기" className="ml-auto" onClick={onClose}><X className="h-4 w-4" /></ToolBtn>
      <ToolBtn label="PNG 내보내기" onClick={onExportPng}><Download className="h-4 w-4" /></ToolBtn>
      <button type="button" onClick={onSave} disabled={saving || !dirty} title="scene 저장"
        className="inline-flex items-center gap-1.5 rounded-full bg-primary px-3 py-1.5 text-caption font-medium text-on-primary transition-colors hover:bg-primary-container focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:opacity-40 disabled:pointer-events-none">
        <Save className="h-3.5 w-3.5" />{saving ? "저장 중…" : "scene 저장"}
      </button>
    </div>
  );
}
