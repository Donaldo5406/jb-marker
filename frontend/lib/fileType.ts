export type FileTypeInfo = {
  label: string; // 트리 배지 텍스트
  fg: string;    // tailwind text-색
  bg: string;    // tailwind bg-색
  lang: string;  // highlight.js 언어
};

const MAP: Record<string, FileTypeInfo> = {
  md:    { label: "MD",  fg: "text-[#0a7d33]", bg: "bg-[#e3f3e8]", lang: "markdown" },
  json:  { label: "{}",  fg: "text-[#953800]", bg: "bg-[#f7e8dc]", lang: "json" },
  scene: { label: "◳",   fg: "text-[#7a3ea8]", bg: "bg-[#efe4f7]", lang: "json" },
  ts:    { label: "TS",  fg: "text-[#0550ae]", bg: "bg-[#dce8fb]", lang: "typescript" },
  tsx:   { label: "TSX", fg: "text-[#0550ae]", bg: "bg-[#dce8fb]", lang: "typescript" },
  png:   { label: "IMG", fg: "text-[#bf3989]", bg: "bg-[#f9e3ef]", lang: "plaintext" },
  jpg:   { label: "IMG", fg: "text-[#bf3989]", bg: "bg-[#f9e3ef]", lang: "plaintext" },
  jpeg:  { label: "IMG", fg: "text-[#bf3989]", bg: "bg-[#f9e3ef]", lang: "plaintext" },
};

const DEFAULT: FileTypeInfo = {
  label: "·", fg: "text-outline", bg: "bg-surface-container-high", lang: "plaintext",
};

export function extOf(name: string): string {
  const i = name.lastIndexOf(".");
  return i >= 0 ? name.slice(i + 1).toLowerCase() : "";
}

/** 경로에서 마지막 세그먼트(파일명). 트리/툴바/드로어 표시 공용. */
export function baseName(path: string): string {
  const segs = path.split("/").filter(Boolean);
  return segs[segs.length - 1] ?? path;
}

export function fileType(name: string): FileTypeInfo {
  return MAP[extOf(name)] ?? DEFAULT;
}

/** 백엔드가 raw 바이트(blob)로 서빙하는 래스터 이미지 확장자.
 *  이런 파일은 텍스트로 fetch(res.json())하면 깨지므로 <img>(useAuthedBlob)로 표시한다. */
const IMAGE_EXTS = new Set(["png", "jpg", "jpeg", "gif", "webp", "avif", "bmp", "ico"]);

export function isImagePath(name: string): boolean {
  return IMAGE_EXTS.has(extOf(name));
}

/** 툴바 표시용 사람친화 이름. .scene는 확장자 대신 의미 라벨. */
export function displayName(name: string): string {
  if (extOf(name) === "scene") return "구조화 씬";
  return name;
}
