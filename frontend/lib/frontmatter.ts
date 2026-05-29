/** 마크다운 선행 YAML frontmatter(`--- ... ---`)를 본문과 분리한다.
 *
 *  brainstorming 산출물(spec.md/plan.md)은 frontmatter가 핵심 메타라, Preview에서
 *  `---` 구분선으로 흘려보내는 대신 별도 메타블록으로 보여주기 위해 사용.
 *  YAML 전체를 파싱하지는 않고 최상위 `key: value` 라인만 추출(들여쓴 라인=중첩값은 건너뜀).
 */
export type FrontmatterEntry = { key: string; value: string };
export type Frontmatter = { entries: FrontmatterEntry[]; raw: string };

export function splitFrontmatter(md: string): { frontmatter: Frontmatter | null; body: string } {
  const text = md ?? "";
  const m = /^\s*---\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)/.exec(text);
  if (!m) return { frontmatter: null, body: text };
  const raw = m[1];
  const body = text.slice(m[0].length);
  const entries: FrontmatterEntry[] = [];
  for (const line of raw.split(/\r?\n/)) {
    if (!line || /^\s/.test(line)) continue; // 최상위 키만(중첩/리스트 항목 제외)
    const idx = line.indexOf(":");
    if (idx <= 0) continue;
    entries.push({ key: line.slice(0, idx).trim(), value: line.slice(idx + 1).trim() });
  }
  return { frontmatter: { entries, raw }, body };
}
