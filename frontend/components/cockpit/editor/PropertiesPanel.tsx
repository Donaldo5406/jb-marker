// frontend/components/cockpit/editor/PropertiesPanel.tsx
"use client";
import * as React from "react";

export type SelectedProps = {
  type: string;
  role?: string;
  text?: string;
  fontSize?: number;
  fill?: string;
  textAlign?: string;
  fontWeight?: string | number;
};

/** 선택 객체 속성 편집. P1=textbox만(내용/크기/색/굵기/정렬). onChange는 부분 patch를 넘긴다. */
export function PropertiesPanel({
  selected, onChange,
}: { selected: SelectedProps | null; onChange: (patch: Record<string, unknown>) => void }) {
  if (!selected) {
    return <p className="px-3 py-3 text-caption text-on-surface-variant">객체를 선택하면 속성이 표시됩니다</p>;
  }
  const isText = selected.type === "textbox";
  return (
    <div className="flex flex-col gap-3 px-3 py-3">
      <div className="text-caption font-semibold text-on-surface">속성 · {selected.role ?? selected.type}</div>
      {isText && (
        <>
          <label className="flex flex-col gap-1 text-caption text-on-surface-variant">
            글자 색
            <input aria-label="글자 색" type="color" value={selected.fill ?? "#000000"}
              onChange={(e) => onChange({ fill: e.target.value })} className="h-7 w-14 rounded border border-outline-variant" />
          </label>
          <label className="flex flex-col gap-1 text-caption text-on-surface-variant">
            글자 크기
            <input aria-label="글자 크기" type="number" min={8} max={400} value={selected.fontSize ?? 48}
              onChange={(e) => onChange({ fontSize: Number(e.target.value) })}
              className="h-7 w-20 rounded border border-outline-variant bg-surface px-2 text-on-surface" />
          </label>
          <label className="flex flex-col gap-1 text-caption text-on-surface-variant">
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
      {!isText && <p className="text-caption text-on-surface-variant">이 객체 유형의 속성 편집은 다음 단계에서 제공됩니다.</p>}
    </div>
  );
}
