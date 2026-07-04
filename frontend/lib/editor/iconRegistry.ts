/** 혜택행 아이콘 — self-host Lucide(MIT) SVG. 허용목록으로 임의 경로 참조를 차단(보안). */
export const ICON_KEYS = [
  "trending-up", "calendar", "coins", "shield", "percent", "gift",
] as const;
const SET = new Set<string>(ICON_KEYS);
export function iconSrc(key: string): string {
  return SET.has(key) ? `/icons/${key}.svg` : "/icons/percent.svg";
}
