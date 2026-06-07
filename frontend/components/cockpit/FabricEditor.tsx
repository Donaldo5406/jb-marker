"use client";

import * as React from "react";
import { Canvas, FabricImage, Textbox } from "fabric";
import "@/lib/fabricDefaults"; // fabric v7 origin(center) → left/top 복원 (side-effect)
import { authedFetch } from "@/lib/api";

export type FabricEditorProps = {
  scene: { objects: any[] } | null;
  onSave: (json: object) => void | Promise<void>;
  width?: number;
  height?: number;
};

/** Fabric.js 대형 캔버스 에디터. scene(Fabric JSON) 로드 + 편집 + 저장.
 *  client-only(EditorPane/FileViewerDrawer에서 next/dynamic ssr:false로 lazy-load). 크롬은 최소. */
export function FabricEditor({ scene, onSave, width = 1080, height = 1080 }: FabricEditorProps) {
  const elRef = React.useRef<HTMLCanvasElement>(null);
  const canvasRef = React.useRef<Canvas | null>(null);
  const [saving, setSaving] = React.useState(false);

  React.useEffect(() => {
    if (!elRef.current) return;
    const canvas = new Canvas(elRef.current, { width, height, backgroundColor: "#fff" });
    canvasRef.current = canvas;
    return () => {
      void canvas.dispose();
      canvasRef.current = null;
    };
  }, [width, height]);

  React.useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !scene) return;
    let cancelled = false;
    const objectUrls: string[] = [];
    canvas.clear();
    const objs = scene.objects ?? [];

    // 1) 텍스트박스를 먼저 동기 렌더 — 이미지 로드 실패/지연이 카피 표시를 막지 않도록.
    for (const o of objs) {
      if (String(o.type ?? "").toLowerCase() !== "textbox") continue;
      const tb = new Textbox(o.text ?? "", {
        left: o.left,
        top: o.top,
        width: o.width,
        fontSize: o.fontSize ?? 48,
        fill: o.fill ?? "#0b1324",
      });
      (tb as any).role = o.role;
      (tb as any).lang = o.lang;
      canvas.add(tb);
    }
    canvas.renderAll();

    // 2) 이미지는 인증 blob으로 로드(vfs 자산은 토큰 필요 — raw fromURL은 401) 후 맨 뒤로.
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
          (img as any).role = o.role;
          canvas.add(img);
          canvas.sendObjectToBack?.(img); // 배경을 텍스트 뒤로
          canvas.renderAll();
        } catch {
          /* 누락/오류 시 스킵 — 텍스트는 이미 렌더됨 */
        }
      }
    })();

    return () => {
      cancelled = true;
      objectUrls.forEach((u) => URL.revokeObjectURL(u));
    };
  }, [scene]);

  const handleSave = async () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    setSaving(true);
    try {
      // fabric v6+: toJSON()은 인자를 받지 않음. 커스텀 prop 직렬화는 toObject([...]) 사용
      // (loadFromJSON이 소비하는 {version,objects,...} 동일 형태).
      await onSave(canvas.toObject(["role", "lang", "slotId"]));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex h-full flex-col bg-surface">
      <div className="flex items-center justify-end gap-2 border-b border-outline-variant bg-surface-container-low px-3 py-2">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="inline-flex items-center gap-1.5 rounded-full bg-primary px-3 py-1.5 text-caption font-medium text-on-primary hover:bg-primary-container disabled:opacity-40"
        >
          {saving ? "저장 중…" : "scene 저장"}
        </button>
      </div>
      <div className="flex-1 overflow-auto bg-surface-container p-4">
        <canvas ref={elRef} className="mx-auto block shadow-ambient" />
      </div>
    </div>
  );
}
