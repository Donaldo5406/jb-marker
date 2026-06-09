/** "data:<mime>;base64,<payload>" → {mime, base64}. 형식이 아니면 null. */
export function parseDataUrl(dataUrl: string): { mime: string; base64: string } | null {
  const m = /^data:([^;,]+);base64,(.*)$/s.exec(dataUrl ?? "");
  if (!m) return null;
  return { mime: m[1], base64: m[2] };
}

/** 파일명 → VFS-safe(영숫자·._- 외는 -, 양끝 - 제거). 확장자는 그대로 보존. */
export function sanitizeAssetName(name: string): string {
  return (name || "image").replace(/[^\w.-]+/g, "-").replace(/^-+|-+$/g, "") || "image";
}

/** asset 저장 rest 경로. seq로 같은 이름 충돌 회피. */
export function assetRestPath(lang: string, name: string, seq: number): string {
  return `design/final/${lang}/assets/${seq}-${sanitizeAssetName(name)}`;
}

export type ImageImportDeps = {
  vfsPut: (rest: string, base64: string, mime: string) => Promise<unknown>;
  assetUrl: (rest: string) => string;
};

/** dataURL(파일 읽기 결과) → VFS asset 저장 + 캔버스 이미지 객체용 src(정본 assetUrl) 반환.
 *  실패(비 data URL) 시 null. 호출부가 src를 FabricImage.assetPath로 세팅해 라운드트립을 보존한다. */
export async function importImageAsset(
  deps: ImageImportDeps, lang: string, fileName: string, dataUrl: string, seq: number,
): Promise<{ src: string; rest: string } | null> {
  const parsed = parseDataUrl(dataUrl);
  if (!parsed) return null;
  const rest = assetRestPath(lang, fileName, seq);
  await deps.vfsPut(rest, parsed.base64, parsed.mime);
  return { src: deps.assetUrl(rest), rest };
}
