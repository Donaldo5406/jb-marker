// frontend/components/cockpit/editor/Inspector.tsx
"use client";
import * as React from "react";
import { LayersPanel } from "./LayersPanel";
import { PropertiesPanel, type SelectedProps } from "./PropertiesPanel";
import type { SceneObject } from "@/lib/editor/sceneSerialize";

/** 우측 인스펙터: 위=레이어, 아래=속성. 세로 스크롤(높이 분할은 부모 Panel이 관리). */
export function Inspector(props: {
  objects: SceneObject[];
  activeIndex: number | null;
  selected: SelectedProps | null;
  onSelect: (i: number) => void;
  onToggleVisible: (i: number) => void;
  onToggleLock: (i: number) => void;
  onForward: (i: number) => void;
  onBackward: (i: number) => void;
  onChangeProps: (patch: Record<string, unknown>) => void;
}) {
  return (
    <div className="flex h-full flex-col overflow-y-auto bg-surface">
      <LayersPanel objects={props.objects} activeIndex={props.activeIndex} onSelect={props.onSelect}
        onToggleVisible={props.onToggleVisible} onToggleLock={props.onToggleLock}
        onForward={props.onForward} onBackward={props.onBackward} />
      <div className="my-1 h-px bg-outline-variant" />
      <PropertiesPanel selected={props.selected} onChange={props.onChangeProps} />
    </div>
  );
}
