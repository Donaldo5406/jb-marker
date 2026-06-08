// frontend/components/cockpit/editor/DesignEditor.tsx
"use client";
import * as React from "react";
import { useFabricCanvas } from "./useFabricCanvas";
import { useEditorHistory } from "./useEditorHistory";
import { Toolbar } from "./Toolbar";
import { Inspector } from "./Inspector";
import { Group, Panel, Separator } from "react-resizable-panels";
import { parseScene, SCENE_CUSTOM_PROPS } from "@/lib/editor/sceneSerialize";
import type { SelectedProps } from "./PropertiesPanel";
import { keyToEditorAction } from "@/lib/editor/shortcuts";

/** .scene 편집 셸. content(.scene JSON 문자열)를 캔버스로, 편집 결과를 onSave(json)로. */
export function DesignEditor({
  content, dirty, onSave, onClose,
}: { content: string; dirty: boolean; onSave: (json: string) => void | Promise<void>; onClose: () => void }) {
  const elRef = React.useRef<HTMLCanvasElement>(null);
  const scene = React.useMemo(() => parseScene(content), [content]);
  const { canvas } = useFabricCanvas(elRef, scene);
  const history = useEditorHistory();
  const [zoom, setZoom] = React.useState(1);
  const [saving, setSaving] = React.useState(false);
  const [revision, setRevision] = React.useState(0);            // 객체 변경 시 인스펙터 갱신
  const [selected, setSelected] = React.useState<SelectedProps | null>(null);
  const [activeIndex, setActiveIndex] = React.useState<number | null>(null);

  const snapshot = React.useCallback(
    () => (canvas ? JSON.stringify(canvas.toObject([...SCENE_CUSTOM_PROPS])) : null), [canvas]);

  // 캔버스 이벤트 → 선택/리비전/히스토리
  React.useEffect(() => {
    if (!canvas) return;
    const sync = () => {
      const objs = canvas.getObjects();
      const active = canvas.getActiveObject();
      const idx = active ? objs.indexOf(active as any) : -1;
      setActiveIndex(idx >= 0 ? idx : null);
      setSelected(active ? (active.toObject([...SCENE_CUSTOM_PROPS]) as SelectedProps) : null);
      setRevision((r) => r + 1);
    };
    const onModified = () => { const s = snapshot(); if (s) history.push(s); sync(); };
    const initial = snapshot(); if (initial) history.reset(initial);
    canvas.on("selection:created", sync);
    canvas.on("selection:updated", sync);
    canvas.on("selection:cleared", sync);
    canvas.on("object:modified", onModified);
    canvas.on("object:added", onModified);
    canvas.on("object:removed", onModified);
    return () => {
      canvas.off("selection:created", sync); canvas.off("selection:updated", sync);
      canvas.off("selection:cleared", sync); canvas.off("object:modified", onModified);
      canvas.off("object:added", onModified); canvas.off("object:removed", onModified);
    };
  }, [canvas, history, snapshot]);

  const restore = React.useCallback((json: string | null) => {
    if (!canvas || !json) return;
    void canvas.loadFromJSON(JSON.parse(json)).then(() => { canvas.renderAll(); setRevision((r) => r + 1); });
  }, [canvas]);

  const doSave = React.useCallback(async () => {
    const s = snapshot(); if (s == null) return;
    setSaving(true);
    try { await onSave(s); } finally { setSaving(false); }
  }, [snapshot, onSave]);

  const applyZoom = React.useCallback((z: number) => {
    if (!canvas) return; const clamped = Math.min(4, Math.max(0.1, z));
    canvas.setZoom(clamped); setZoom(clamped); canvas.renderAll();
  }, [canvas]);

  const duplicateActive = React.useCallback(async () => {
    if (!canvas) return; const a = canvas.getActiveObject(); if (!a) return;
    const clone = await a.clone([...SCENE_CUSTOM_PROPS]);
    clone.set({ left: (a.left ?? 0) + 20, top: (a.top ?? 0) + 20 });
    canvas.add(clone); canvas.setActiveObject(clone); canvas.renderAll();
  }, [canvas]);

  const deleteActive = React.useCallback(() => {
    if (!canvas) return; const a = canvas.getActiveObject(); if (!a) return;
    canvas.remove(a); canvas.discardActiveObject(); canvas.renderAll();
  }, [canvas]);

  // 키보드 단축키(텍스트 인라인 편집 중에는 무시)
  React.useEffect(() => {
    if (!canvas) return;
    const onKey = (e: KeyboardEvent) => {
      const editing = (canvas.getActiveObject() as any)?.isEditing;
      if (editing) return;
      const action = keyToEditorAction(e);
      if (!action) return;
      e.preventDefault();
      if (action === "undo") restore(history.undo());
      else if (action === "redo") restore(history.redo());
      else if (action === "duplicate") void duplicateActive();
      else if (action === "delete") deleteActive();
      else if (action === "save") void doSave();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [canvas, history, restore, duplicateActive, deleteActive, doSave]);

  // 인스펙터용 현재 객체 배열(리비전 의존).
  const objects = React.useMemo(
    () => (canvas ? canvas.getObjects().map((o) => o.toObject([...SCENE_CUSTOM_PROPS])) : []),
    [canvas, revision]);

  const opAt = (i: number) => (canvas ? canvas.getObjects()[i] : null);
  const onChangeProps = (patch: Record<string, unknown>) => {
    const a = canvas?.getActiveObject(); if (!a || !canvas) return;
    a.set(patch); canvas.renderAll();
    const s = snapshot(); if (s) history.push(s);
    setSelected(a.toObject([...SCENE_CUSTOM_PROPS]) as SelectedProps);
  };

  return (
    <div className="flex h-full min-h-0 flex-col bg-surface">
      <Group orientation="horizontal" className="min-h-0 flex-1 overflow-hidden">
        <Panel id="de-canvas" defaultSize={72} minSize={40} className="min-h-0 overflow-auto bg-surface-container">
          <div className="flex min-h-full items-center justify-center p-6">
            <canvas ref={elRef} className="block shadow-ambient" />
          </div>
        </Panel>
        <Separator className="w-px bg-outline-variant data-[separator=hover]:bg-on-surface-variant" />
        <Panel id="de-inspector" defaultSize={28} minSize={18} className="min-h-0 overflow-hidden border-l border-outline-variant">
          <Inspector
            objects={objects} activeIndex={activeIndex} selected={selected}
            onSelect={(i) => { const o = opAt(i); if (o && canvas) { canvas.setActiveObject(o); canvas.renderAll(); } }}
            onToggleVisible={(i) => { const o = opAt(i); if (o && canvas) { o.visible = !o.visible; canvas.renderAll(); setRevision((r) => r + 1); } }}
            onToggleLock={(i) => { const o = opAt(i); if (o && canvas) { const lock = o.evented !== false; o.evented = !lock; o.selectable = !lock; canvas.renderAll(); setRevision((r) => r + 1); } }}
            onForward={(i) => { const o = opAt(i); if (o && canvas) { canvas.bringObjectForward(o); canvas.renderAll(); setRevision((r) => r + 1); } }}
            onBackward={(i) => { const o = opAt(i); if (o && canvas) { canvas.sendObjectBackwards(o); canvas.renderAll(); setRevision((r) => r + 1); } }}
            onChangeProps={onChangeProps}
          />
        </Panel>
      </Group>
      <Toolbar
        canUndo={history.canUndo} canRedo={history.canRedo} zoom={zoom} saving={saving} dirty={dirty}
        onUndo={() => restore(history.undo())} onRedo={() => restore(history.redo())}
        onZoomIn={() => applyZoom(zoom + 0.1)} onZoomOut={() => applyZoom(zoom - 0.1)} onZoomFit={() => applyZoom(1)}
        onSave={() => void doSave()} onClose={onClose}
      />
    </div>
  );
}
