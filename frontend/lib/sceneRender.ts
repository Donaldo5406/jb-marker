// @ts-ignore
import { fabric } from "fabric";

/** Fabric scene JSON → composite PNG dataURL.
 *  임시 off-DOM StaticCanvas에 로드해 toDataURL("image/png")로 직렬화.
 *  M4 FabricEditor와 동일 라이브러리(spec §8.2). */
export async function renderSceneToPng(
  sceneJson: any,
  opts: { width?: number; height?: number } = {}
): Promise<string> {
  const c = new (fabric as any).StaticCanvas(null, {
    width: opts.width ?? 1080,
    height: opts.height ?? 1080,
  });
  await new Promise<void>((resolve) => c.loadFromJSON(sceneJson, resolve));
  c.renderAll();
  const url = c.toDataURL({ format: "png" }) as string;
  c.dispose();
  return url;
}

async function dataUrlToBlob(dataUrl: string): Promise<Blob> {
  const resp = await fetch(dataUrl);
  return await resp.blob();
}

/** Blob → ArrayBuffer (jsdom 호환 폴백). jsdom의 Blob에는 arrayBuffer가 없을 수 있어
 *  FileReader.readAsArrayBuffer로 대체. */
async function blobToArrayBuffer(blob: Blob): Promise<ArrayBuffer> {
  if (typeof (blob as any).arrayBuffer === "function") {
    return await blob.arrayBuffer();
  }
  return await new Promise<ArrayBuffer>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = () => reject(reader.error);
    reader.readAsArrayBuffer(blob);
  });
}

/** Blob(PNG) → base64 → PUT /vfs (path: /{run}/review/_render/{lang}.png).
 *  VFS는 텍스트/json 기반 — base64 인코딩으로 전송, mime=image/png 표시. */
export async function uploadRender(
  runId: string,
  lang: string,
  blob: Blob,
  baseUrl: string = "/api"
): Promise<void> {
  const buf = await blobToArrayBuffer(blob);
  const b64 = btoa(String.fromCharCode(...new Uint8Array(buf)));
  const body = {
    run_id: runId,
    path: `/${runId}/review/_render/${lang}.png`,
    content: b64,
    content_encoding: "base64",
    mime: "image/png",
    source: "frontend",
  };
  await fetch(`${baseUrl}/vfs`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

/** 모든 언어 일괄 렌더+업로드. 실패한 언어는 graceful skip
 *  (백엔드 R1이 vision_skipped로 흡수, spec §5.2/§9). */
export async function renderAndUploadAll(
  runId: string,
  scenes: Record<string, any>,
  baseUrl?: string
): Promise<string[]> {
  const uploaded: string[] = [];
  for (const [lang, scene] of Object.entries(scenes)) {
    try {
      const url = await renderSceneToPng(scene);
      const blob = await dataUrlToBlob(url);
      await uploadRender(runId, lang, blob, baseUrl);
      uploaded.push(lang);
    } catch {
      // graceful: 실패한 언어는 스킵, 백엔드 R1이 vision_skipped로 흡수
    }
  }
  return uploaded;
}
