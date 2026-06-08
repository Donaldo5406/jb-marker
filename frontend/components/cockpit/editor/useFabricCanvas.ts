import * as React from "react";
import { Canvas, FabricImage, Textbox } from "fabric";
import "@/lib/fabricDefaults"; // fabric v7 origin(center)→left/top 복원(side-effect)
import { authedFetch } from "@/lib/api";
import type { ParsedScene } from "@/lib/editor/sceneSerialize";

/** Fabric 캔버스 생성/해제 + 씬 로드. 캔버스 인스턴스를 state로 노출(준비되면 리렌더).
 *  텍스트는 동기 렌더(이미지 지연이 카피 표시를 막지 않게), 이미지는 인증 blob 후 맨 뒤로. */
export function useFabricCanvas(
  elRef: React.RefObject<HTMLCanvasElement>,
  scene: ParsedScene | null,
) {
  const [canvas, setCanvas] = React.useState<Canvas | null>(null);
  const width = scene?.width ?? 1080;
  const height = scene?.height ?? 1080;

  React.useEffect(() => {
    if (!elRef.current) return;
    const c = new Canvas(elRef.current, { width, height, backgroundColor: "#fff" });
    setCanvas(c);
    return () => { void c.dispose(); setCanvas(null); };
  }, [elRef, width, height]);

  React.useEffect(() => {
    if (!canvas || !scene) return;
    let cancelled = false;
    const urls: string[] = [];
    canvas.clear();
    const objs = scene.objects ?? [];
    for (const o of objs) {
      if (String(o.type ?? "").toLowerCase() !== "textbox") continue;
      const tb = new Textbox(o.text ?? "", { left: o.left, top: o.top, width: o.width, fontSize: o.fontSize ?? 48, fill: o.fill ?? "#0b1324" });
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
          const url = URL.createObjectURL(await res.blob());
          urls.push(url);
          const img = await FabricImage.fromURL(url);
          if (cancelled) return;
          img.set({ left: o.left, top: o.top });
          if (o.width) img.scaleToWidth(o.width);
          (img as any).role = o.role; (img as any).slotId = o.slotId;
          canvas.add(img);
          canvas.sendObjectToBack?.(img);
          canvas.renderAll();
        } catch { /* 누락/오류 스킵 — 텍스트는 이미 렌더됨 */ }
      }
    })();
    return () => { cancelled = true; urls.forEach((u) => URL.revokeObjectURL(u)); };
  }, [canvas, scene]);

  return { canvas };
}
