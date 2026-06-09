// frontend/components/cockpit/editor/DesignEditor.tsx
"use client";
import * as React from "react";
import { Textbox, Rect, Circle, Line, FabricImage, Ellipse, filters as fabricFilters } from "fabric";
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
import { buildFabricFilters, type FilterParams } from "@/lib/editor/imageFilters";
import { buildClipPath, type MaskKind } from "@/lib/editor/clipMask";
import { computeAspectCrop, type AspectKey } from "@/lib/editor/imageCrop";
import { exportFilename, triggerPngDownload } from "@/lib/editor/exportPng";
import { RasterEditModal } from "./RasterEditModal";
import { editedAssetName, computeRasterSwap } from "@/lib/editor/rasterEdit";
import { useCockpit } from "../CockpitProvider";
import { api, authedFetch } from "@/lib/api";

// 모듈 스코프 상수(fabricFilters는 모듈 import라 안정) — 매 렌더 재생성/useCallback deps 노이즈 회피.
const FILTER_CTORS = {
  Brightness: fabricFilters.Brightness, Contrast: fabricFilters.Contrast,
  Saturation: fabricFilters.Saturation, Blur: fabricFilters.Blur, Grayscale: fabricFilters.Grayscale,
};

/** .scene 편집 셸. content(.scene JSON 문자열)를 캔버스로, 편집 결과를 onSave(json)로. */
export function DesignEditor({
  content, dirty: _dirty, onSave, onClose,
}: { content: string; dirty: boolean; onSave: (json: string) => void | Promise<void>; onClose: () => void }) {
  void _dirty; // 외부 dirty prop은 더 이상 사용하지 않음(저장버튼은 내부 dirty로 구동). 시그니처는 유지.
  const { runId, designLang } = useCockpit();
  const elRef = React.useRef<HTMLCanvasElement>(null);
  const scene = React.useMemo(() => parseScene(content), [content]);
  const { canvas, loadingRef, loadVersion } = useFabricCanvas(elRef, scene);
  const history = useEditorHistory();
  const { push: pushHistory, undo: undoHistory, redo: redoHistory, reset: resetHistory, canUndo, canRedo } = history;
  const [zoom, setZoom] = React.useState(1);
  const [saving, setSaving] = React.useState(false);
  const [dirty, setDirty] = React.useState(false);
  const [revision, setRevision] = React.useState(0);
  const [selected, setSelected] = React.useState<SelectedProps | null>(null);
  const [activeIndex, setActiveIndex] = React.useState<number | null>(null);
  const [selCount, setSelCount] = React.useState(0);              // 정렬 버튼 노출 판정(1+ 선택)
  // 픽셀 리터칭 모달: 열림·소스 objectURL·원본 파일명·대상 fabric 이미지 객체.
  const [raster, setRaster] = React.useState<{ source: string; fileName: string; target: any } | null>(null);
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

  // 캔버스 준비 + 매 씬 로드(이미지 포함) 완료 시 히스토리 baseline 재설정.
  // loadVersion을 deps에 포함 → 언어 전환 등 재로드 후에도 깨끗한 baseline + dirty=false 보장.
  React.useEffect(() => {
    if (!canvas) return;
    const s = snapshot();
    if (s) resetHistory(s);
    setDirty(false);
  }, [canvas, loadVersion, snapshot, resetHistory]);

  // 활성 이미지의 정본(assetPath ?? src)을 blob로 받아 objectURL을 filerobot source로. 텍스트/도형은 무시.
  // 캔버스 이벤트 effect(아래)의 deps에 참조되므로 그보다 먼저 선언한다(TDZ 회피).
  const openRasterEdit = React.useCallback(async (obj?: any) => {
    const a = obj ?? (canvas?.getActiveObject() as any);
    if (!a || String(a.type).toLowerCase() !== "image") return;
    const srcPath = String(a.assetPath ?? a.src ?? "");
    if (!srcPath) return;
    try {
      const res = await authedFetch(srcPath);
      if (!res.ok) return;
      const objUrl = URL.createObjectURL(await res.blob());
      importedUrlsRef.current.push(objUrl);
      const fileName = srcPath.split("/").pop() || "image.png";
      setRaster({ source: objUrl, fileName, target: a });
    } catch { /* 소스 로드 실패 — 무시 */ }
  }, [canvas]);

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
      // restore(undo/redo) 또는 프로그램적 씬 로드(useFabricCanvas) 중에는 사용자 편집이 아니므로
      // dirty/history를 건드리지 않는다(배경 이미지 비동기 추가가 열자마자 dirty로 오인되는 것 방지).
      if (restoringRef.current || loadingRef.current) { sync(); return; }
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
    const onDblClick = (e: any) => {
      const t = e.target;
      if (t && String(t.type).toLowerCase() === "image") void openRasterEdit(t);
    };
    canvas.on("mouse:dblclick", onDblClick);
    return () => {
      canvas.off("selection:created", sync); canvas.off("selection:updated", sync);
      canvas.off("selection:cleared", sync); canvas.off("object:modified", onModified);
      canvas.off("object:added", onModified); canvas.off("object:removed", onModified);
      canvas.off("object:moving", onMoving);
      canvas.off("mouse:dblclick", onDblClick);
    };
  }, [canvas, snapshot, pushHistory, scene, loadingRef, openRasterEdit]);  // loadingRef는 안정적 ref(useFabricCanvas) — lint 충족용

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
    // 먼저 스케일(>600px 다운스케일) 후 스케일된 치수로 중앙 배치 — scaleToWidth는 left/top을 옮기지 않으므로
    // 순서를 반대로 하면 큰 이미지가 화면 밖으로 밀려난다.
    if ((img.width ?? 0) > 600) img.scaleToWidth(600);
    img.set({ left: cx - img.getScaledWidth() / 2, top: cy - img.getScaledHeight() / 2 });
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

  // 활성 이미지에 비파괴 보정 적용 후 직렬화 스냅샷을 selected에 반영(toObject가 filters/clipPath/crop 직렬화).
  const afterImageEdit = React.useCallback((a: any) => {
    canvas!.renderAll();
    setDirty(true);
    const s = snapshot(); if (s) pushHistory(s);
    setSelected(a.toObject([...SCENE_CUSTOM_PROPS]) as SelectedProps);
    setRevision((r) => r + 1);
  }, [canvas, snapshot, pushHistory]);
  const applyFilters = React.useCallback((params: FilterParams) => {
    const a = canvas?.getActiveObject() as any; if (!a || !canvas) return;
    if (String(a.type).toLowerCase() !== "image") return;
    a.filters = buildFabricFilters(params, FILTER_CTORS);
    a.applyFilters();
    afterImageEdit(a);
  }, [canvas, afterImageEdit]);
  const applyMask = React.useCallback((kind: MaskKind) => {
    const a = canvas?.getActiveObject() as any; if (!a || !canvas) return;
    if (String(a.type).toLowerCase() !== "image") return;
    const cp = buildClipPath(kind, { width: a.width ?? 0, height: a.height ?? 0 }, { Rect, Ellipse });
    a.clipPath = cp ?? undefined;
    afterImageEdit(a);
  }, [canvas, afterImageEdit]);
  const applyCrop = React.useCallback((aspect: AspectKey) => {
    const a = canvas?.getActiveObject() as any; if (!a || !canvas) return;
    if (String(a.type).toLowerCase() !== "image") return;
    const el = a.getElement?.();
    const natW = el?.naturalWidth || el?.width || a.width || 0;
    const natH = el?.naturalHeight || el?.height || a.height || 0;
    a.set(computeAspectCrop(natW, natH, aspect));
    afterImageEdit(a);
  }, [canvas, afterImageEdit]);
  // 라이브 캔버스를 1:1 뷰포트로 캡처(현재 보정 반영) → PNG 다운로드. 선택 핸들 제외 위해 선택 해제.
  const exportPng = React.useCallback(() => {
    if (!canvas) return;
    canvas.discardActiveObject();
    const vt = canvas.viewportTransform ? ([...canvas.viewportTransform] as any) : null;
    const z = canvas.getZoom();
    canvas.setViewportTransform([1, 0, 0, 1, 0, 0]); canvas.renderAll();
    const url = canvas.toDataURL({ format: "png", multiplier: 1 });
    if (vt) canvas.setViewportTransform(vt);
    canvas.setZoom(z); canvas.renderAll();
    triggerPngDownload(url, exportFilename(designLang));
  }, [canvas, designLang]);

  // filerobot 저장 결과(dataURL) → 새 VFS asset(원본 보존) → 활성 이미지 src/assetPath 교체.
  // setElement은 filters가 남아있으면 새 이미지에 재적용하므로 먼저 filters/clipPath/crop을 초기화한다.
  const applyRaster = React.useCallback(async (dataUrl: string, fullName: string) => {
    const target = raster?.target;
    if (!canvas || !runId || !target) { setRaster(null); return; }
    const ext = (fullName.split(".").pop() || "png").toLowerCase();
    const deps = {
      vfsPut: (rest: string, b64: string, mime: string) => api.vfsPut(runId, rest, b64, mime, "base64"),
      assetUrl: (rest: string) => api.assetUrl(runId, rest),
    };
    const saved = await importImageAsset(
      deps, designLang, editedAssetName(fullName, ext), dataUrl, importSeqRef.current++);
    if (!saved) { setRaster(null); return; }
    const res = await authedFetch(saved.src);
    if (!res.ok) { setRaster(null); return; }
    const objUrl = URL.createObjectURL(await res.blob());
    importedUrlsRef.current.push(objUrl);
    const prevScaledW = (target.width ?? 0) * (target.scaleX ?? 1);
    // P3 비파괴 보정 초기화(이중 적용·차원 불일치 방지) 후 새 픽셀로 교체.
    target.filters = [];
    target.clipPath = undefined;
    await target.setSrc(objUrl);                       // width/height = 새 자연치수로 리셋
    const { scaleX, scaleY } = computeRasterSwap(prevScaledW, target.width ?? 0);
    target.set({ cropX: 0, cropY: 0, scaleX, scaleY });
    (target as any).assetPath = saved.src;             // P3 재로드 정본 경로(필수: src와 함께 교체)
    setRaster(null);
    afterImageEdit(target);                            // renderAll + dirty + history + selected 동기
  }, [canvas, runId, designLang, raster, afterImageEdit]);

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
            onApplyFilters={applyFilters} onApplyMask={applyMask} onApplyCrop={applyCrop}
            onRasterEdit={() => void openRasterEdit()}
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
        onExportPng={exportPng}
      />
      {raster && (
        <RasterEditModal
          open source={raster.source} fileName={raster.fileName}
          onApply={(dataUrl, fullName) => void applyRaster(dataUrl, fullName)}
          onClose={() => setRaster(null)}
        />
      )}
    </div>
  );
}
