/** 업로드 파일 → VFS PUT 준비 유틸 — 대상 경로·타입·크기·인코딩 규약의 단일 출처. */

const TEXT_EXTS = ["md", "txt", "csv", "json"];
const IMAGE_EXTS = ["png", "jpg", "jpeg"];
export const TEXT_MAX = 256 * 1024;        // 256KB
export const IMAGE_MAX = 5 * 1024 * 1024;  // 5MB
/** 업로드를 소비하는 스튜디오만 노출(백엔드 소비 접점과 짝). */
export const UPLOAD_STUDIOS = ["brainstorming", "design", "review"] as const;

function ext(name: string): string {
  const i = name.lastIndexOf(".");
  return i < 0 ? "" : name.slice(i + 1).toLowerCase();
}

export function uploadKind(name: string): "text" | "image" | null {
  const e = ext(name);
  if (TEXT_EXTS.includes(e)) return "text";
  if (IMAGE_EXTS.includes(e)) return "image";
  return null;
}

/** 경로 구분자·특수문자를 _로 — VFS 경로 세그먼트 안전화(한글·영숫자·._- 보존).
 *  치환 결과가 _로 시작하면 제거한다 — FileTree가 _ 접두 세그먼트를 내부용으로
 *  간주해 숨기므로, 업로드는 성공했는데 트리에 안 보이는 상태를 막는다.
 *  전부 제거돼 빈 문자열이 되면 안전 기본값 "file"을 쓴다. */
export function sanitizeFilename(name: string): string {
  const sanitized = name.replace(/[^\w.\-가-힣]/g, "_").replace(/^_+/, "");
  return sanitized || "file";
}

export function uploadTargetPath(studio: string, filename: string): string {
  return `${studio}/uploads/${sanitizeFilename(filename)}`;
}

export function uploadMime(name: string, kind: "text" | "image"): string {
  const e = ext(name);
  if (kind === "image") return e === "png" ? "image/png" : "image/jpeg";
  if (e === "json") return "application/json";
  if (e === "csv") return "text/csv";
  return "text/markdown";
}

export function validateSize(kind: "text" | "image", size: number): string | null {
  if (kind === "text" && size > TEXT_MAX) return "텍스트 파일은 256KB까지 업로드할 수 있어요";
  if (kind === "image" && size > IMAGE_MAX) return "이미지는 5MB까지 업로드할 수 있어요";
  return null;
}

/** File → 텍스트(jsdom 호환 폴백). jsdom의 File/Blob에는 text()가 없을 수 있어
 *  FileReader.readAsText로 대체(sceneRender.ts의 blobToArrayBuffer와 동일 패턴). */
async function readFileAsText(file: File): Promise<string> {
  if (typeof (file as unknown as { text?: unknown }).text === "function") {
    return await file.text();
  }
  return await new Promise<string>((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result));
    r.onerror = () => reject(r.error);
    r.readAsText(file);
  });
}

/** PUT 본문 준비 — 텍스트는 원문, 이미지는 base64(vfs PUT content_encoding 규약). */
export async function readForPut(
  file: File, kind: "text" | "image",
): Promise<{ content: string; encoding?: "base64" }> {
  if (kind === "text") return { content: await readFileAsText(file) };
  const dataUrl = await new Promise<string>((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result));
    r.onerror = () => reject(r.error);
    r.readAsDataURL(file);
  });
  return { content: dataUrl.split(",")[1] ?? "", encoding: "base64" };
}
