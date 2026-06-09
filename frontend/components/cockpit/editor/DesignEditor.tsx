// frontend/components/cockpit/editor/DesignEditor.tsx
"use client";
import * as React from "react";
import { Textbox, Rect, Circle, Line, FabricImage } from "fabric";
import { useFabricCanvas } from "./useFabricCanvas";
import { useEditorHistory } from "./useEditorHistory";
import { Toolbar } from "./Toolbar";
import { Inspector } from "./Inspector";
import { Group, Panel, Separator } from "react-resizable-panels";
import { parseScene, SCENE_CUSTOM_PROPS } from "@/lib/editor/sceneSerialize";
import type { SelectedProps } from "./PropertiesPanel";
import { keyToEditorAction } from "@/lib/editor/shortcuts";
import { buildObjectSpec, type NewObjectKind } from "@/lib/editor/objectFactory";
import { importImageAsset } from "@/lib/editor/imageImport";
import { alignBoxes, distributeBoxes, snapValue, type Box, type AlignMode } from "@/lib/editor/align";
import { useCockpit } from "../CockpitProvider";
import { api, authedFetch } from "@/lib/api";

/** .scene 편집 셸. content(.scene JSON 문자열)를 캔버스로, 편집 결과를 onSave(json)로. */
export function DesignEditor({
  content, dirty: _dirty, onSave, onClose,
}: { content: string; dirty: boolean; onSave: (json: string) => void | Promise<void>; onClose: () => void }) {
  void _dirty; // 외부 dirty prop은 더 이상 사용하지 않음(저장버튼은 내부 dirty로 구동). 시그니처는 유지.
  const { runId, designLang } = useCockpit();
  const elRef = React.useRef<HTMLCanvasElement>(null);
  const scene = React.useMemo(() => parseScene(content), [content]);
  const { canvas } = useFabricCanvas(elRef, scene);
  const history = useEditorHistory();
  const { push: pushHistory, undo: undoHistory, redo: redoHistory, reset: resetHistory, canUndo, canRedo } = history;
  const [zoom, setZoom] = React.useState(1);
  const [saving, setSaving] = React.useState(false);
  const [dirty, setDirty] = React.useState(false);
  const [revision, setRevision] = React.useState(0);
  const [selected, setSelected] = React.useState<SelectedProps | null>(null);
  const [activeIndex, setActiveIndex] = React.useState<number | null>(null);
  const [selCount, setSelCount] = React.useState(0);              // 정렬 버튼 노출 판정(1+ 선택)
  const restoringRef = React.useRef(false);
  const importSeqRef = React.useRef(0);                            // asset 파일명 충돌 회피용 시퀀스
  const importedUrlsRef = React.useRef<string[]>([]);              // import objectURL — 언마운트 시 revoke
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const cx = (scene?.width ?? 1080) / 2;
  const cy = (scene?.height ?? 1080) / 2;

  const snapshot = React.useCallback(
    () => (canvas ? JSON.stringify(canvas.toObject([...SCENE_CUSTOM_PROPS])) : null), [canvas]);

  // 이벤트를 발화하지 않는 변경(정렬 등) 후 히스토리/일관성을 수동 반영.
  const commit = React.useCallback(() => {
    if (!canvas) return;
    setDirty(true);
    const s = snapshot(); if (s) pushHistory(s);
    setRevision((r) => r + 1);
  }, [canvas, snapshot, pushHistory]);

  // Fabric 객체 → 절대 좌표 Box. fabricDefaults가 origin을 left/top로 복원하므로 left/top=좌상단.
  const boxOf = (o: any): Box => ({
    left: o.left ?? 0, top: o.top ?? 0,
    width: (o.width ?? 0) * (o.scaleX ?? 1), height: (o.height ?? 0) * (o.scaleY ?? 1),
  });

  const alignSelection = React.useCallback((mode: AlignMode) => {
    if (!canvas) return;
    const objs = canvas.getActiveObjects();
    if (objs.length === 0) return;
    canvas.discardActiveObject();   // 다중 선택을 해제해 각 객체를 절대 좌표로 복원
    const bounds: Box = { left: 0, top: 0, width: scene?.width ?? 1080, height: scene?.height ?? 1080 };
    const patches = alignBoxes(objs.map(boxOf), mode, bounds);
    objs.forEach((o, i) => o.set(patches[i]));
    canvas.requestRenderAll();
    commit();
  }, [canvas, scene, commit]);

  const distributeSelection = React.useCallback((axis: "h" | "v") => {
    if (!canvas) return;
    const objs = canvas.getActiveObjects();
    if (objs.length < 3) return;
    canvas.discardActiveObject();
    const patches = distributeBoxes(objs.map(boxOf), axis);
    objs.forEach((o, i) => o.set(patches[i]));
    canvas.requestRenderAll();
    commit();
  }, [canvas, commit]);

  React.useEffect(() => {
    if (!canvas) return;
    const s = snapshot();
    if (s) resetHistory(s);
    setDirty(false);
  }, [canvas, snapshot, resetHistory]);

  React.useEffect(() => {
    if (!canvas) return;
    const sync = () => {
      const objs = canvas.getObjects();
      const active = canvas.getActiveObject();
      const idx = active ? objs.indexOf(active as any) : -1;
      setActiveIndex(idx >= 0 ? idx : null);
      setSelected(active ? (active.toObject([...SCENE_CUSTOM_PROPS]) as SelectedProps) : null);
      setSelCount(canvas.getActiveObjects().length);
      setRevision((r) => r + 1);
    };
    const onModified = () => {
      if (restoringRef.current) { sync(); return; }
      setDirty(true);
      const s = snapshot(); if (s) pushHistory(s); sync();
    };
    // 드래그 중 캔버스 가장자리/중앙 + 다른 객체의 좌/중앙/우(상/중앙/하)로 스냅.
    const SNAP = 8;
    const onMoving = (e: any) => {
      const o = e.target; if (!o) return;
      const W = scene?.width ?? 1080; const H = scene?.height ?? 1080;
      const others = canvas.getObjects().filter((x) => x !== o);
      const w = (o.width ?? 0) * (o.scaleX ?? 1); const h = (o.height ?? 0) * (o.scaleY ?? 1);
      const xs = [0, W / 2 - w / 2, W - w]; const ys = [0, H / 2 - h / 2, H - h];
      for (const x of others) { const bw = (x.width ?? 0) * (x.scaleX ?? 1); xs.push(x.left ?? 0, (x.left ?? 0) + bw / 2 - w / 2, (x.left ?? 0) + bw - w); }
      for (const y of others) { const bh = (y.height ?? 0) * (y.scaleY ?? 1); ys.push(y.top ?? 0, (y.top ?? 0) + bh / 2 - h / 2, (y.top ?? 0) + bh - h); }
      const sx = snapValue(o.left ?? 0, xs, SNAP); if (sx != null) o.set({ left: sx });
      const sy = snapValue(o.top ?? 0, ys, SNAP); if (sy != null) o.set({ top: sy });
    };
    canvas.on("selection:created", sync);
    canvas.on("selection:updated", sync);
    canvas.on("selection:cleared", sync);
    canvas.on("object:modified", onModified);
    canvas.on("object:added", onModified);
    canvas.on("object:removed", onModified);
    canvas.on("object:moving", onMoving);
    return () => {
      canvas.off("selection:created", sync); canvas.off("selection:updated", sync);
      canvas.off("selection:cleared", sync); canvas.off("object:modified", onModified);
      canvas.off("object:added", onModified); canvas.off("object:removed", onModified);
      canvas.off("object:moving", onMoving);
    };
  }, [canvas, snapshot, pushHistory, scene]);

  // import objectURL 누수 방지(언마운트 시).
  React.useEffect(() => () => { importedUrlsRef.current.forEach((u) => URL.revokeObjectURL(u)); }, []);

  const restore = React.useCallback((json: string | null) => {
    if (!canvas || !json) return;
    restoringRef.current = true;
    void canvas.loadFromJSON(JSON.parse(json))
      .then(() => { canvas.renderAll(); setRevision((r) => r + 1); })
      .finally(() => { restoringRef.current = false; });
  }, [canvas]);

  const doSave = React.useCallback(async () => {
    const s = snapshot(); if (s == null) return;
    setSaving(true);
    try { await onSave(s); setDirty(false); } finally { setSaving(false); }
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

  // 새 객체 추가(텍스트/도형/선). canvas.add가 object:added를 발화 → 히스토리/dirty 자동.
  const addObject = React.useCallback((kind: NewObjectKind) => {
    if (!canvas) return;
    const spec = buildObjectSpec(kind, { x: cx, y: cy });
    let obj;
    if (spec.ctor === "rect") obj = new Rect(spec.props);
    else if (spec.ctor === "circle") obj = new Circle(spec.props);
    else if (spec.ctor === "line") { const { points, ...rest } = spec.props; obj = new Line(points, rest); }
    else obj = new Textbox(spec.props.text, spec.props);
    canvas.add(obj); canvas.setActiveObject(obj); canvas.renderAll();
  }, [canvas, cx, cy]);

  // 이미지 import: 파일 → dataURL → VFS asset(base64) → assetUrl로 재로드(blob) → 캔버스 추가.
  const importFile = React.useCallback(async (file: File) => {
    if (!canvas || !runId) return;
    const dataUrl = await new Promise<string>((resolve, reject) => {
      const fr = new FileReader();
      fr.onload = () => resolve(String(fr.result));
      fr.onerror = () => reject(fr.error);
      fr.readAsDataURL(file);
    });
    const deps = {
      vfsPut: (rest: string, b64: string, mime: string) => api.vfsPut(runId, rest, b64, mime, "base64"),
      assetUrl: (rest: string) => api.assetUrl(runId, rest),
    };
    const result = await importImageAsset(deps, designLang, file.name, dataUrl, importSeqRef.current++);
    if (!result) return;
    // 정본 assetUrl을 다시 받아 blob로 렌더(인라인 base64가 .scene에 박히지 않게).
    const res = await authedFetch(result.src);
    if (!res.ok) return;
    const objUrl = URL.createObjectURL(await res.blob());
    importedUrlsRef.current.push(objUrl);
    const img = await FabricImage.fromURL(objUrl);
    img.set({ left: cx - (img.width ?? 0) / 2, top: cy - (img.height ?? 0) / 2 });
    if ((img.width ?? 0) > 600) img.scaleToWidth(600);
    (img as any).role = "imported";
    (img as any).assetPath = result.src;     // 저장-재로드 정본 경로
    canvas.add(img); canvas.setActiveObject(img); canvas.renderAll();
  }, [canvas, runId, designLang, cx, cy]);

  const onPickFile = React.useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]; if (f) void importFile(f);
    e.target.value = "";  // 같은 파일 재선택 허용
  }, [importFile]);

  const onDropCanvas = React.useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f && f.type.startsWith("image/")) void importFile(f);
  }, [importFile]);

  // 키보드 단축키(텍스트 인라인 편집/폼 입력 중에는 무시)
  React.useEffect(() => {
    if (!canvas) return;
    const onKey = (e: KeyboardEvent) => {
      const ae = document.activeElement as HTMLElement | null;
      const tag = ae?.tagName;
      if (ae && (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || ae.isContentEditable)) return;
      const editing = (canvas.getActiveObject() as any)?.isEditing;
      if (editing) return;
      const action = keyToEditorAction(e);
      if (!action) return;
      e.preventDefault();
      if (action === "undo") restore(undoHistory());
      else if (action === "redo") restore(redoHistory());
      else if (action === "duplicate") void duplicateActive();
      else if (action === "delete") deleteActive();
      else if (action === "save") void doSave();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [canvas, undoHistory, redoHistory, restore, duplicateActive, deleteActive, doSave]);

  const objects = React.useMemo(
    () => (canvas ? canvas.getObjects().map((o) => o.toObject([...SCENE_CUSTOM_PROPS])) : []),
    [canvas, revision]);

  const opAt = (i: number) => (canvas ? canvas.getObjects()[i] : null);
  const onChangeProps = (patch: Record<string, unknown>) => {
    const a = canvas?.getActiveObject(); if (!a || !canvas) return;
    a.set(patch); canvas.renderAll();
    setDirty(true);
    const s = snapshot(); if (s) pushHistory(s);
    setSelected(a.toObject([...SCENE_CUSTOM_PROPS]) as SelectedProps);
    setRevision((r) => r + 1);
  };

  return (
    <div className="flex h-full min-h-0 flex-col bg-surface">
      <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={onPickFile} />
      <Group orientation="horizontal" className="min-h-0 flex-1 overflow-hidden">
        <Panel id="de-canvas" defaultSize={72} minSize={40} className="min-h-0 overflow-auto bg-surface-container">
          <div className="flex min-h-full items-center justify-center p-6"
            onDragOver={(e) => e.preventDefault()} onDrop={onDropCanvas}>
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
        canUndo={canUndo} canRedo={canRedo} zoom={zoom} saving={saving} dirty={dirty} canAlign={selCount >= 1}
        onUndo={() => restore(undoHistory())} onRedo={() => restore(redoHistory())}
        onZoomIn={() => applyZoom(zoom + 0.1)} onZoomOut={() => applyZoom(zoom - 0.1)} onZoomFit={() => applyZoom(1)}
        onSave={() => void doSave()} onClose={onClose}
        onAddText={() => addObject("textbox")} onAddRect={() => addObject("rect")}
        onAddCircle={() => addObject("circle")} onAddLine={() => addObject("line")}
        onImportImage={() => fileInputRef.current?.click()}
        onAlign={alignSelection} onDistribute={distributeSelection}
      />
    </div>
  );
}
