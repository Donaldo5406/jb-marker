/** 사용자가 수동 저장한 언어 목록을 담는 VFS 파일 경로(언더스코어=하네스 비노출 관례). */
export const EDITED_PATH = "design/_edited.json";

/** 중복 없이 lang 추가. */
export function addLang(list: string[], lang: string): string[] {
  return list.includes(lang) ? list : [...list, lang];
}

/** _edited.json content_text → 언어 배열(깨지면 []). */
export function parseEdited(content: string | null | undefined): string[] {
  if (!content) return [];
  try {
    const o = JSON.parse(content) as { langs?: unknown };
    return Array.isArray(o.langs) ? o.langs.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}
