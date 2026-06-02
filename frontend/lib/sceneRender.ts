import { StaticCanvas } from "fabric";
import "./fabricDefaults"; // fabric v7 origin(center) → left/top 복원 (side-effect)

/** Fabric scene JSON → composite PNG dataURL.
 *  임시 off-DOM StaticCanvas에 로드해 toDataURL("image/png")로 직렬화.
 *  M4 FabricEditor와 동일 라이브러리(spec §8.2). v6 named import + Promise-returning loadFromJSON. */
export async function renderSceneToPng(
  sceneJson: any,
  opts: { width?: number; height?: number } = {}
): Promise<string> {
  const c = new StaticCanvas(undefined, {
    width: opts.width ?? 1080,
    height: opts.height ?? 1080,
  });
  // v6 시그니처: loadFromJSON(json, reviver?, {signal}?) → Promise<this>
  await c.loadFromJSON(sceneJson);
  c.renderAll();
  const url = c.toDataURL({ format: "png", multiplier: 1 }) as string;
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

/** Uint8Array → base64. 큰 버퍼(300KB+ PNG)에서 spread는 스택 초과 위험이 있으므로
 *  8KB chunk로 String.fromCharCode를 호출해 누적. */
function arrayBufferToBase64(buf: ArrayBuffer): string {
  let bin = "";
  const arr = new Uint8Array(buf);
  const chunk = 0x8000;
  for (let i = 0; i < arr.length; i += chunk) {
    const slice = arr.subarray(i, i + chunk);
    bin += String.fromCharCode.apply(null, Array.from(slice));
  }
  return btoa(bin);
}

/** Blob(PNG) → base64 → PUT /vfs/{runId}/{rest} (path-based, api.ts:52-56 미러).
 *  PutText 모델 호환: {content: b64, content_encoding: "base64", mime: "image/png"}.
 *  백엔드는 content_encoding == "base64"일 때 base64.b64decode → bytes 저장. */
export async function uploadRender(
  runId: string,
  lang: string,
  blob: Blob,
  baseUrl: string = "/api"
): Promise<void> {
  const buf = await blobToArrayBuffer(blob);
  const b64 = arrayBufferToBase64(buf);
  const rest = `review/_render/${lang}.png`;
  const body = {
    content: b64,
    content_encoding: "base64",
    mime: "image/png",
  };
  const resp = await fetch(`${baseUrl}/vfs/${runId}/${rest}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    throw new Error(`uploadRender failed: ${resp.status}`);
  }
}

/** 모든 언어 일괄 렌더+업로드. 실패한 언어는 graceful skip
 *  (백엔드 R1이 vision_skipped로 흡수, spec §5.2/§9). 성공한 lang만 반환. */
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
