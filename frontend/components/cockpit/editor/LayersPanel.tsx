"use client";
import * as React from "react";
import { Eye, EyeOff, Lock, Unlock, ChevronUp, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { toLayers } from "@/lib/editor/layersModel";
import type { SceneObject } from "@/lib/editor/sceneSerialize";

export function LayersPanel({
  objects, activeIndex, onSelect, onToggleVisible, onToggleLock, onForward, onBackward,
}: {
  objects: SceneObject[];
  activeIndex: number | null;
  onSelect: (index: number) => void;
  onToggleVisible: (index: number) => void;
  onToggleLock: (index: number) => void;
  onForward: (index: number) => void;
  onBackward: (index: number) => void;
}) {
  const rows = toLayers(objects);
  return (
    <div className="flex flex-col">
      <div className="px-3 py-2 text-caption font-semibold text-on-surface">레이어</div>
      {rows.length === 0 && <p className="px-3 py-2 text-caption text-on-surface-variant">객체 없음</p>}
      <ul>
        {rows.map((r) => (
          <li key={r.index} className={cn("flex items-center gap-1 px-2 py-1", activeIndex === r.index && "bg-surface-container-high")}>
            <button type="button" aria-label={`레이어 선택: ${r.label}`} onClick={() => onSelect(r.index)}
              className="min-w-0 flex-1 truncate text-left text-caption text-on-surface">{r.label}</button>
            <button type="button" aria-label={`가시성: ${r.label}`} onClick={() => onToggleVisible(r.index)}
              className="text-on-surface-variant hover:text-on-surface">{r.visible ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}</button>
            <button type="button" aria-label={`잠금: ${r.label}`} onClick={() => onToggleLock(r.index)}
              className="text-on-surface-variant hover:text-on-surface">{r.locked ? <Lock className="h-3.5 w-3.5" /> : <Unlock className="h-3.5 w-3.5" />}</button>
            <button type="button" aria-label={`앞으로: ${r.label}`} onClick={() => onForward(r.index)}
              className="text-on-surface-variant hover:text-on-surface"><ChevronUp className="h-3.5 w-3.5" /></button>
            <button type="button" aria-label={`뒤로: ${r.label}`} onClick={() => onBackward(r.index)}
              className="text-on-surface-variant hover:text-on-surface"><ChevronDown className="h-3.5 w-3.5" /></button>
          </li>
        ))}
      </ul>
    </div>
  );
}
