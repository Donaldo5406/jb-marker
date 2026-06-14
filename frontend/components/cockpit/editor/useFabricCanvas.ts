import * as React from "react";
import { Canvas, FabricImage, Rect, Textbox } from "fabric";
import "@/lib/fabricDefaults"; // fabric v7 origin(center)→left/top 복원(side-effect)
import { authedFetch } from "@/lib/api";
import type { ParsedScene } from "@/lib/editor/sceneSerialize";

/** Fabric 캔버스 생성/해제 + 씬 로드. 캔버스 인스턴스를 state로 노출(준비되면 리렌더).
 *  텍스트는 동기 렌더(이미지 지연이 카피 표시를 막지 않게), 이미지는 인증 blob 후 맨 뒤로.
 *  ⚠️ `scene`은 참조가 안정적이어야 한다(호출부에서 useMemo). 로드 완료 시 loadVersion이 증가해
 *     리렌더가 발생하는데, 매 렌더 새 scene 객체를 넘기면 로드 effect가 재실행되어 루프가 된다. */
export function useFabricCanvas(
  elRef: React.RefObject<HTMLCanvasElement>,
  scene: ParsedScene | null,
) {
  const [canvas, setCanvas] = React.useState<Canvas | null>(null);
  // 프로그램적 씬 로드 구간 표시(true면 호출부가 object:added를 사용자 편집으로 오인하지 않음).
  const loadingRef = React.useRef(false);
  // 씬 로드(이미지까지) 완료 시 증가 — 호출부가 이 시점에 히스토리 baseline을 다시 잡는다.
  const [loadVersion, setLoadVersion] = React.useState(0);
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
    loadingRef.current = true;          // 로드 시작 — 동기 텍스트/비동기 이미지 추가를 사용자 편집과 구분
    const urls: string[] = [];
    canvas.clear();
    const objs = scene.objects ?? [];
    for (const o of objs) {
      const t = String(o.type ?? "").toLowerCase();
      if (t === "rect") {
        // 스크림(텍스트 가독성 배경) — assembleScene이 텍스트보다 먼저(낮은 z) 배치.
        // 보조 배경이라 비선택(텍스트 클릭 시 스크림이 잡히지 않게). 저장 직렬화엔 포함됨.
        const r = new Rect({ left: o.left, top: o.top, width: o.width, height: o.height,
          fill: o.fill, rx: o.rx, ry: o.ry, selectable: false, evented: false });
        (r as any).role = o.role; (r as any).slotId = o.slotId;
        canvas.add(r);
      } else if (t === "textbox") {
        const tb = new Textbox(o.text ?? "", { left: o.left, top: o.top, width: o.width, fontSize: o.fontSize ?? 48, fill: o.fill ?? "#0b1324" });
        (tb as any).role = o.role; (tb as any).lang = o.lang; (tb as any).slotId = o.slotId;
        canvas.add(tb);
      }
    }
    canvas.renderAll();
    void (async () => {
      for (const o of objs) {
        if (String(o.type ?? "").toLowerCase() !== "image") continue;
        // Fabric Image.toObject은 src에 blob: objectURL을 직렬화한다 → 저장본 재로드 시 죽은 URL.
        // assetPath(정본 VFS URL)가 있으면 그것을, 없으면(조립 직후 씬) src를 쓴다.
        const srcPath = String(o.assetPath ?? o.src ?? "");
        if (!srcPath) continue;
        try {
          const res = await authedFetch(srcPath);
          if (!res.ok) continue;
          const url = URL.createObjectURL(await res.blob());
          urls.push(url);
          // 에디터 저장본(toObject)은 scaleX를 가져 fromObject로 전체 복원(scale·crop·filters·clipPath·opacity).
          // 어셈블러 씬(scaleX 없음, width=슬롯 표시폭)은 기존대로 fromURL+scaleToWidth로 슬롯에 맞춘다.
          let img: FabricImage;
          if (o.scaleX != null) {
            img = await FabricImage.fromObject({ ...o, src: url } as any);
          } else {
            img = await FabricImage.fromURL(url);
            img.set({ left: o.left, top: o.top });
            if (o.width) img.scaleToWidth(o.width);
          }
          if (cancelled) return;
          (img as any).role = o.role; (img as any).slotId = o.slotId; (img as any).assetPath = srcPath;
          canvas.add(img);
          // background(풀 포스터)만 맨 뒤로. 로고 등 다른 이미지는 맨 앞으로 올려 배경에 가리지
          // 않게 한다(이미지를 일괄 sendToBack 하면 나중에 추가된 로고가 배경보다 더 뒤로 가
          // 완전히 가려졌다 — '로고 z 최하라 안 보임' 회귀).
          if (String((o as any).role) === "background") canvas.sendObjectToBack?.(img);
          else canvas.bringObjectToFront?.(img);
          canvas.renderAll();
        } catch { /* 누락/오류 스킵 — 텍스트는 이미 렌더됨 */ }
      }
      if (!cancelled) { loadingRef.current = false; setLoadVersion((v) => v + 1); }  // 로드 완료 → baseline 재설정 신호
    })();
    return () => { cancelled = true; loadingRef.current = false; urls.forEach((u) => URL.revokeObjectURL(u)); };
  }, [canvas, scene]);

  return { canvas, loadingRef, loadVersion };
}
