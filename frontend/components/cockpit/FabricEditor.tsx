"use client";

import * as React from "react";
import { Canvas, FabricImage, Textbox, Rect, filters } from "fabric";
import {
  Type, ImagePlus, Square, Copy, Trash2, ArrowUp, ArrowDown, Undo2, Redo2,
  AlignLeft, AlignCenter, AlignRight, Bold,
} from "lucide-react";
import "@/lib/fabricDefaults"; // fabric v7 origin(center) → left/top 복원 (side-effect)
import { authedFetch } from "@/lib/api";
import {
  SCENE_EXPORT_PROPS, DEFAULT_FILTERS, clampFilter, buildSavePayload,
  initHistory, pushSnapshot, undo as histUndo, redo as histRedo,
  canUndo, canRedo, type FilterValues, type History,
} from "@/lib/fabricEditorTools";

export type FabricEditorProps = {
  scene: { objects: any[] } | null;
  onSave: (json: object) => void | Promise<void>;
  width?: number;
  height?: number;
};

const EXPORT = SCENE_EXPORT_PROPS as unknown as string[];

/** 선택 객체의 패널 표시용 미러(반응형). canvas 객체는 React state로 직접 못 들고 옴. */
type Sel = {
  kind: "text" | "image" | "shape";
  fontSize: number; fontWeight: string; fill: string; textAlign: string; opacity: number;
} | null;

/** Fabric.js 편집기(Tier 2) — scene(Fabric JSON) 로드 + 툴바·속성·필터·undo/redo + 저장.
 *  client-only(next/dynamic ssr:false lazy-load). scene 계약(role/lang/slotId·치수) 보존. */
export function FabricEditor({ scene, onSave, width = 1080, height = 1080 }: FabricEditorProps) {
  const elRef = React.useRef<HTMLCanvasElement>(null);
  const canvasRef = React.useRef<Canvas | null>(null);
  const loadingRef = React.useRef(false);   // scene 로드 중 → object:added 스냅샷 억제
  const restoringRef = React.useRef(false);  // undo/redo loadFromJSON 중 → 스냅샷 억제
  const histRef = React.useRef<History>(initHistory("{}"));
  const [hist, setHist] = React.useState<History>(histRef.current);
  const [sel, setSel] = React.useState<Sel>(null);
  const [filterVals, setFilterVals] = React.useState<FilterValues>(DEFAULT_FILTERS);
  const [saving, setSaving] = React.useState(false);

  const setHistory = (h: History) => { histRef.current = h; setHist(h); };
  const snapshot = React.useCallback(() => {
    const c = canvasRef.current;
    if (!c || loadingRef.current || restoringRef.current) return;
    setHistory(pushSnapshot(histRef.current, JSON.stringify(c.toObject(EXPORT))));
  }, []);

  const readSel = React.useCallback(() => {
    const c = canvasRef.current;
    const o: any = c?.getActiveObject();
    if (!o) { setSel(null); return; }
    const type = String(o.type ?? "").toLowerCase();
    const kind: "text" | "image" | "shape" =
      type === "textbox" || type === "text" ? "text" : type === "image" ? "image" : "shape";
    setSel({
      kind,
      fontSize: Number(o.fontSize ?? 40),
      fontWeight: String(o.fontWeight ?? "normal"),
      fill: typeof o.fill === "string" ? o.fill : "#0b1324",
      textAlign: String(o.textAlign ?? "left"),
      opacity: Number(o.opacity ?? 1),
    });
    setFilterVals({ ...DEFAULT_FILTERS }); // 필터 슬라이더는 선택마다 0에서 시작(증분 적용)
  }, []);

  // 1) 캔버스 1회 init + 이벤트 와이어링.
  React.useEffect(() => {
    if (!elRef.current) return;
    const canvas = new Canvas(elRef.current, { width, height, backgroundColor: "#fff" });
    canvasRef.current = canvas;
    const onSelect = () => readSel();
    const onClear = () => setSel(null);
    canvas.on("selection:created", onSelect);
    canvas.on("selection:updated", onSelect);
    canvas.on("selection:cleared", onClear);
    canvas.on("object:modified", snapshot);
    canvas.on("object:added", snapshot);
    canvas.on("object:removed", snapshot);
    return () => { void canvas.dispose(); canvasRef.current = null; };
  }, [width, height, readSel, snapshot]);

  // 2) scene 로드 — 텍스트 동기 → 이미지 비동기(인증 blob). 로드 후 히스토리 초기화.
  React.useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !scene) return;
    let cancelled = false;
    const objectUrls: string[] = [];
    loadingRef.current = true;
    canvas.clear();
    canvas.backgroundColor = "#fff";
    const objs = scene.objects ?? [];

    for (const o of objs) {
      if (String(o.type ?? "").toLowerCase() !== "textbox") continue;
      const tb = new Textbox(o.text ?? "", {
        left: o.left, top: o.top, width: o.width,
        fontSize: o.fontSize ?? 48, fill: o.fill ?? "#0b1324",
        fontWeight: o.fontWeight ?? "normal", textAlign: o.textAlign ?? "left",
      });
      (tb as any).role = o.role; (tb as any).lang = o.lang; (tb as any).slotId = o.slotId;
      canvas.add(tb);
    }
    canvas.renderAll();

    void (async () => {
      for (const o of objs) {
        if (String(o.type ?? "").toLowerCase() !== "image" || !o.src) continue;
        try {
          const res = await authedFetch(String(o.src));
          if (!res.ok) continue;
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          objectUrls.push(url);
          const img = await FabricImage.fromURL(url);
          if (cancelled) return;
          img.set({ left: o.left, top: o.top });
          if (o.width) img.scaleToWidth(o.width);
          (img as any).role = o.role; (img as any).slotId = o.slotId;
          canvas.add(img);
          canvas.sendObjectToBack?.(img);
          canvas.renderAll();
        } catch { /* 누락/오류 시 스킵 */ }
      }
      if (!cancelled) {
        loadingRef.current = false;
        setHistory(initHistory(JSON.stringify(canvas.toObject(EXPORT))));
      }
    })();

    return () => { cancelled = true; objectUrls.forEach((u) => URL.revokeObjectURL(u)); };
  }, [scene]);

  // --- 객체 변형 헬퍼 ---
  const withActive = (fn: (c: Canvas, o: any) => void) => {
    const c = canvasRef.current; const o = c?.getActiveObject();
    if (!c || !o) return;
    fn(c, o); c.requestRenderAll();
  };
  const patchActive = (props: Record<string, unknown>) => {
    withActive((c, o) => { o.set(props); snapshot(); });
    setSel((s) => (s ? { ...s, ...props } as Sel : s));
  };

  const addText = () => {
    const c = canvasRef.current; if (!c) return;
    const tb = new Textbox("텍스트를 입력하세요", { left: 120, top: 120, width: 480, fontSize: 48, fill: "#0b1324" });
    c.add(tb); c.setActiveObject(tb); c.requestRenderAll(); readSel();
  };
  const addRect = () => {
    const c = canvasRef.current; if (!c) return;
    const r = new Rect({ left: 140, top: 140, width: 280, height: 160, fill: "#2f6df6", rx: 12, ry: 12 });
    c.add(r); c.setActiveObject(r); c.requestRenderAll(); readSel();
  };
  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; const c = canvasRef.current;
    if (!file || !c) return;
    const url = URL.createObjectURL(file);
    try {
      const img = await FabricImage.fromURL(url);
      if (img.width && img.width > 600) img.scaleToWidth(600);
      img.set({ left: 100, top: 100 });
      c.add(img); c.setActiveObject(img); c.requestRenderAll(); readSel();
    } finally { e.target.value = ""; }
  };
  const duplicate = () => withActive(async (c, o) => {
    const clone = await o.clone(EXPORT);
    clone.set({ left: (o.left ?? 0) + 24, top: (o.top ?? 0) + 24 });
    c.add(clone); c.setActiveObject(clone); c.requestRenderAll();
  });
  const remove = () => withActive((c, o) => { c.remove(o); c.discardActiveObject(); setSel(null); });
  const forward = () => withActive((c, o) => { c.bringObjectForward(o); snapshot(); });
  const backward = () => withActive((c, o) => { c.sendObjectBackwards(o); snapshot(); });

  const applyFilters = (next: FilterValues) => {
    setFilterVals(next);
    withActive((c, o) => {
      if (String(o.type ?? "").toLowerCase() !== "image") return;
      const fs: any[] = [];
      if (next.brightness) fs.push(new filters.Brightness({ brightness: clampFilter(next.brightness) }));
      if (next.contrast) fs.push(new filters.Contrast({ contrast: clampFilter(next.contrast) }));
      if (next.saturation) fs.push(new filters.Saturation({ saturation: clampFilter(next.saturation) }));
      o.filters = fs; o.applyFilters(); snapshot();
    });
  };

  const restore = (snap: string | null, h: History) => {
    const c = canvasRef.current; if (!c || snap === null) return;
    restoringRef.current = true;
    void c.loadFromJSON(snap).then(() => {
      c.renderAll(); restoringRef.current = false; setSel(null);
    });
    setHistory(h);
  };
  const doUndo = () => { const [h, snap] = histUndo(histRef.current); restore(snap, h); };
  const doRedo = () => { const [h, snap] = histRedo(histRef.current); restore(snap, h); };

  const handleSave = async () => {
    const canvas = canvasRef.current; if (!canvas) return;
    setSaving(true);
    try {
      // 계약 보존: toObject(role/lang/slotId) + 캔버스 치수(aspect). fabricEditorTools.buildSavePayload.
      await onSave(buildSavePayload(canvas.toObject(EXPORT), width, height));
    } finally { setSaving(false); }
  };

  const Btn = ({ onClick, title, disabled, children }: {
    onClick: () => void; title: string; disabled?: boolean; children: React.ReactNode;
  }) => (
    <button type="button" onClick={onClick} title={title} aria-label={title} disabled={disabled}
      className="inline-flex h-8 w-8 items-center justify-center rounded-md text-on-surface-variant hover:bg-surface-container-high disabled:opacity-30">
      {children}
    </button>
  );

  return (
    <div className="flex h-full flex-col bg-surface">
      {/* 툴바 */}
      <div className="flex flex-wrap items-center gap-1 border-b border-outline-variant bg-surface-container-low px-2 py-1.5">
        <Btn onClick={addText} title="텍스트 추가"><Type className="h-4 w-4" /></Btn>
        <label title="이미지 추가" aria-label="이미지 추가"
          className="inline-flex h-8 w-8 cursor-pointer items-center justify-center rounded-md text-on-surface-variant hover:bg-surface-container-high">
          <ImagePlus className="h-4 w-4" />
          <input type="file" accept="image/*" className="hidden" onChange={onUpload} data-testid="image-upload" />
        </label>
        <Btn onClick={addRect} title="도형 추가"><Square className="h-4 w-4" /></Btn>
        <span className="mx-1 h-5 w-px bg-outline-variant" />
        <Btn onClick={duplicate} title="복제" disabled={!sel}><Copy className="h-4 w-4" /></Btn>
        <Btn onClick={remove} title="삭제" disabled={!sel}><Trash2 className="h-4 w-4" /></Btn>
        <Btn onClick={forward} title="앞으로" disabled={!sel}><ArrowUp className="h-4 w-4" /></Btn>
        <Btn onClick={backward} title="뒤로" disabled={!sel}><ArrowDown className="h-4 w-4" /></Btn>
        <span className="mx-1 h-5 w-px bg-outline-variant" />
        <Btn onClick={doUndo} title="실행 취소" disabled={!canUndo(hist)}><Undo2 className="h-4 w-4" /></Btn>
        <Btn onClick={doRedo} title="다시 실행" disabled={!canRedo(hist)}><Redo2 className="h-4 w-4" /></Btn>
        <button type="button" onClick={handleSave} disabled={saving}
          className="ml-auto inline-flex items-center gap-1.5 rounded-full bg-primary px-3 py-1.5 text-caption font-medium text-on-primary hover:bg-primary-container disabled:opacity-40">
          {saving ? "저장 중…" : "scene 저장"}
        </button>
      </div>

      <div className="flex min-h-0 flex-1">
        {/* 캔버스 */}
        <div className="flex-1 overflow-auto bg-surface-container p-4">
          <canvas ref={elRef} className="mx-auto block shadow-ambient" />
        </div>

        {/* 속성 패널 */}
        <aside className="w-56 shrink-0 space-y-4 overflow-y-auto border-l border-outline-variant bg-surface-container-low p-3" data-testid="props-panel">
          {!sel ? (
            <p className="text-caption text-on-surface-variant">객체를 선택하면 속성이 표시됩니다.</p>
          ) : (
            <>
              {sel.kind === "text" && (
                <div className="space-y-2">
                  <div className="text-caption font-medium text-on-surface">텍스트</div>
                  <label className="block text-caption text-on-surface-variant">크기
                    <input type="number" min={8} max={400} value={sel.fontSize}
                      onChange={(e) => patchActive({ fontSize: Number(e.target.value) })}
                      className="mt-0.5 w-full rounded border border-outline-variant bg-surface-container-lowest px-2 py-1 text-body-sm text-on-surface" />
                  </label>
                  <div className="flex items-center gap-1">
                    <Btn onClick={() => patchActive({ fontWeight: sel.fontWeight === "bold" ? "normal" : "bold" })} title="굵게"><Bold className="h-4 w-4" /></Btn>
                    <Btn onClick={() => patchActive({ textAlign: "left" })} title="왼쪽 정렬"><AlignLeft className="h-4 w-4" /></Btn>
                    <Btn onClick={() => patchActive({ textAlign: "center" })} title="가운데 정렬"><AlignCenter className="h-4 w-4" /></Btn>
                    <Btn onClick={() => patchActive({ textAlign: "right" })} title="오른쪽 정렬"><AlignRight className="h-4 w-4" /></Btn>
                  </div>
                  <label className="flex items-center justify-between text-caption text-on-surface-variant">색상
                    <input type="color" value={/^#/.test(sel.fill) ? sel.fill : "#0b1324"}
                      onChange={(e) => patchActive({ fill: e.target.value })}
                      className="h-7 w-10 cursor-pointer rounded border border-outline-variant bg-transparent" />
                  </label>
                </div>
              )}
              {sel.kind === "shape" && (
                <label className="flex items-center justify-between text-caption text-on-surface-variant">채움 색
                  <input type="color" value={/^#/.test(sel.fill) ? sel.fill : "#2f6df6"}
                    onChange={(e) => patchActive({ fill: e.target.value })}
                    className="h-7 w-10 cursor-pointer rounded border border-outline-variant bg-transparent" />
                </label>
              )}
              {sel.kind === "image" && (
                <div className="space-y-2">
                  <div className="text-caption font-medium text-on-surface">이미지 보정</div>
                  {([["brightness", "밝기"], ["contrast", "대비"], ["saturation", "채도"]] as const).map(([k, label]) => (
                    <label key={k} className="block text-caption text-on-surface-variant">{label}
                      <input type="range" min={-1} max={1} step={0.05} value={filterVals[k]}
                        onChange={(e) => applyFilters({ ...filterVals, [k]: Number(e.target.value) })}
                        className="mt-0.5 w-full" data-testid={`filter-${k}`} />
                    </label>
                  ))}
                </div>
              )}
              <label className="block text-caption text-on-surface-variant">불투명도
                <input type="range" min={0} max={1} step={0.05} value={sel.opacity}
                  onChange={(e) => patchActive({ opacity: Number(e.target.value) })}
                  className="mt-0.5 w-full" />
              </label>
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
