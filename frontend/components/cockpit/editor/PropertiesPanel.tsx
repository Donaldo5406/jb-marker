// frontend/components/cockpit/editor/PropertiesPanel.tsx
"use client";
import * as React from "react";
import { ImageFilterControls } from "./ImageFilterControls";
import type { FilterParams } from "@/lib/editor/imageFilters";
import type { MaskKind } from "@/lib/editor/clipMask";
import type { AspectKey } from "@/lib/editor/imageCrop";

export type SelectedProps = {
  type: string;
  role?: string;
  text?: string;
  fontSize?: number;
  fill?: string;
  textAlign?: string;
  fontWeight?: string | number;
  stroke?: string;
  strokeWidth?: number;
  rx?: number;
  radius?: number;
  opacity?: number;
  filters?: any[];
  cropX?: number;
  cropY?: number;
  clipPath?: any;
};

const SHAPE_TYPES = new Set(["rect", "circle", "triangle", "ellipse", "line", "path"]);

/** 선택 객체 속성 편집. 유형별 분기(textbox / 도형 / 이미지). onChange는 부분 patch를 넘긴다. */
export function PropertiesPanel({
  selected, onChange, onApplyFilters, onApplyMask, onApplyCrop,
}: {
  selected: SelectedProps | null;
  onChange: (patch: Record<string, unknown>) => void;
  onApplyFilters?: (params: FilterParams) => void;
  onApplyMask?: (kind: MaskKind) => void;
  onApplyCrop?: (aspect: AspectKey) => void;
}) {
  if (!selected) {
    return <p className="px-3 py-3 text-caption text-on-surface-variant">객체를 선택하면 속성이 표시됩니다</p>;
  }
  const isText = selected.type === "textbox";
  const isShape = SHAPE_TYPES.has(selected.type);
  const isImage = selected.type === "image";
  const labelCls = "flex flex-col gap-1 text-caption text-on-surface-variant";
  const numCls = "h-7 w-20 rounded border border-outline-variant bg-surface px-2 text-on-surface";
  const colorCls = "h-7 w-14 rounded border border-outline-variant";
  return (
    <div className="flex flex-col gap-3 px-3 py-3">
      <div className="text-caption font-semibold text-on-surface">속성 · {selected.role ?? selected.type}</div>

      {isText && (
        <>
          <label className={labelCls}>
            글자 색
            <input aria-label="글자 색" type="color" value={selected.fill ?? "#000000"}
              onChange={(e) => onChange({ fill: e.target.value })} className={colorCls} />
          </label>
          <label className={labelCls}>
            글자 크기
            <input aria-label="글자 크기" type="number" min={8} max={400} value={selected.fontSize ?? 48}
              onChange={(e) => onChange({ fontSize: Number(e.target.value) })} className={numCls} />
          </label>
          <label className={labelCls}>
            정렬
            <select aria-label="정렬" value={selected.textAlign ?? "left"}
              onChange={(e) => onChange({ textAlign: e.target.value })}
              className="h-7 w-24 rounded border border-outline-variant bg-surface px-2 text-on-surface">
              <option value="left">왼쪽</option><option value="center">가운데</option><option value="right">오른쪽</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-caption text-on-surface-variant">
            <input aria-label="굵게" type="checkbox" checked={selected.fontWeight === "bold" || selected.fontWeight === 700}
              onChange={(e) => onChange({ fontWeight: e.target.checked ? "bold" : "normal" })} />
            굵게
          </label>
        </>
      )}

      {isShape && (
        <>
          <label className={labelCls}>
            채움 색
            <input aria-label="채움 색" type="color" value={selected.fill ?? "#3b82f6"}
              onChange={(e) => onChange({ fill: e.target.value })} className={colorCls} />
          </label>
          <label className={labelCls}>
            테두리 색
            <input aria-label="테두리 색" type="color" value={selected.stroke ?? "#000000"}
              onChange={(e) => onChange({ stroke: e.target.value })} className={colorCls} />
          </label>
          <label className={labelCls}>
            테두리 두께
            <input aria-label="테두리 두께" type="number" min={0} max={80} value={selected.strokeWidth ?? 0}
              onChange={(e) => onChange({ strokeWidth: Number(e.target.value) })} className={numCls} />
          </label>
          {selected.type === "rect" && (
            <label className={labelCls}>
              모서리 둥글기
              <input aria-label="모서리 둥글기" type="number" min={0} max={200} value={selected.rx ?? 0}
                onChange={(e) => onChange({ rx: Number(e.target.value), ry: Number(e.target.value) })} className={numCls} />
            </label>
          )}
        </>
      )}

      {isImage && (
        <>
          <label className={labelCls}>
            투명도
            <input aria-label="투명도" type="range" min={0} max={1} step={0.05} value={selected.opacity ?? 1}
              onChange={(e) => onChange({ opacity: Number(e.target.value) })} className="w-32" />
          </label>
          <ImageFilterControls
            filters={selected.filters} clipPath={selected.clipPath}
            onApplyFilters={onApplyFilters ?? (() => {})}
            onApplyMask={onApplyMask ?? (() => {})}
            onApplyCrop={onApplyCrop ?? (() => {})}
          />
        </>
      )}

      {!isText && !isShape && !isImage && (
        <p className="text-caption text-on-surface-variant">이 객체 유형의 속성 편집은 다음 단계에서 제공됩니다.</p>
      )}
    </div>
  );
}
