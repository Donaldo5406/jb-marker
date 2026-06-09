// frontend/components/cockpit/editor/ImageFilterControls.tsx
"use client";
import * as React from "react";
import { extractFilterParams, FILTER_DEFAULTS, type FilterParams } from "@/lib/editor/imageFilters";
import { maskKindOf, type MaskKind } from "@/lib/editor/clipMask";
import type { AspectKey } from "@/lib/editor/imageCrop";

/** 이미지 비파괴 보정 UI: 필터 슬라이더(밝기/대비/채도/흐림)·흑백·마스크·종횡비 크롭.
 *  값은 선택 객체의 직렬화 스냅샷(filters/clipPath)에서 파생(컨트롤드). 크롭은 한 방향 적용이라 비제어. */
export function ImageFilterControls({
  filters, clipPath, onApplyFilters, onApplyMask, onApplyCrop,
}: {
  filters: any[] | undefined;
  clipPath: any | undefined;
  onApplyFilters: (params: FilterParams) => void;
  onApplyMask: (kind: MaskKind) => void;
  onApplyCrop: (aspect: AspectKey) => void;
}) {
  const params = extractFilterParams(filters);
  const mask = maskKindOf(clipPath);
  const labelCls = "flex flex-col gap-1 text-caption text-on-surface-variant";
  const selCls = "h-7 w-28 rounded border border-outline-variant bg-surface px-2 text-on-surface";
  const set = (patch: Partial<FilterParams>) => onApplyFilters({ ...params, ...patch });
  return (
    <div className="flex flex-col gap-3 border-t border-outline-variant pt-3">
      <div className="text-caption font-semibold text-on-surface">보정</div>
      <label className={labelCls}>밝기
        <input aria-label="밝기" type="range" min={-1} max={1} step={0.05} value={params.brightness}
          onChange={(e) => set({ brightness: Number(e.target.value) })} className="w-full" />
      </label>
      <label className={labelCls}>대비
        <input aria-label="대비" type="range" min={-1} max={1} step={0.05} value={params.contrast}
          onChange={(e) => set({ contrast: Number(e.target.value) })} className="w-full" />
      </label>
      <label className={labelCls}>채도
        <input aria-label="채도" type="range" min={-1} max={1} step={0.05} value={params.saturation}
          onChange={(e) => set({ saturation: Number(e.target.value) })} className="w-full" />
      </label>
      <label className={labelCls}>흐림
        <input aria-label="흐림" type="range" min={0} max={1} step={0.02} value={params.blur}
          onChange={(e) => set({ blur: Number(e.target.value) })} className="w-full" />
      </label>
      <label className="flex items-center gap-2 text-caption text-on-surface-variant">
        <input aria-label="흑백" type="checkbox" checked={params.grayscale}
          onChange={(e) => set({ grayscale: e.target.checked })} />
        흑백
      </label>
      <button type="button" className="self-start text-caption text-primary hover:underline"
        onClick={() => onApplyFilters({ ...FILTER_DEFAULTS })}>보정 초기화</button>
      <label className={labelCls}>마스크
        <select aria-label="마스크" value={mask} onChange={(e) => onApplyMask(e.target.value as MaskKind)} className={selCls}>
          <option value="none">없음</option>
          <option value="rounded">둥근 사각형</option>
          <option value="circle">원형</option>
          <option value="ellipse">타원</option>
        </select>
      </label>
      <label className={labelCls}>크롭 비율
        <select aria-label="크롭 비율" defaultValue="free" onChange={(e) => onApplyCrop(e.target.value as AspectKey)} className={selCls}>
          <option value="free">자유(원본)</option>
          <option value="1:1">1:1</option>
          <option value="4:5">4:5</option>
          <option value="16:9">16:9</option>
        </select>
      </label>
    </div>
  );
}
