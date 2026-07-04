import { api, type VfsNode } from "@/lib/api";

export type ReviewVerdict = {
  verdict_id?: string;
  node: "legal" | "i18n";
  asset_id?: string;
  lang?: string | null;
  severity: "critical" | "warning";
  location?: {
    slot?: string;
    bbox?: { x: number; y: number; w: number; h: number };
    image?: string;
  } & Record<string, unknown>;
  evidence?: string;
  clause?: string;
  official_source_url?: string;
  kind?: string;
  disclosure?: string;
};

function restOf(runId: string, path: string): string {
  return path.replace(`/${runId}/`, "");
}

/** review/legal·i18n 하위의 verdict.json을 모두 fetch·파싱(파싱 실패는 graceful skip). */
export async function loadReviewVerdicts(runId: string, nodes: VfsNode[]): Promise<ReviewVerdict[]> {
  const targets = nodes.filter((n) => /\/review\/(legal|i18n)\/[^/]+\/verdict\.json$/.test(n.path));
  const out: ReviewVerdict[] = [];
  for (const n of targets) {
    try {
      const node = await api.vfsGet(runId, restOf(runId, n.path));
      if (node.content_text) out.push(JSON.parse(node.content_text) as ReviewVerdict);
    } catch {
      /* 누락/파싱 실패 — 건너뜀 */
    }
  }
  return out;
}

/** report.md 본문(frontmatter 제거). 없으면 null. */
export async function loadReviewReport(runId: string): Promise<string | null> {
  try {
    const node = await api.vfsGet(runId, "review/report.md");
    const t = node.content_text ?? "";
    const body = t.replace(/^---[\s\S]*?---\n/, "").trim();
    return body || null;
  } catch {
    return null;
  }
}

/** 백엔드 pin_sort_key와 동일 계약: critical 우선, 다음 verdict_id 사전순. */
function pinSortKey(v: ReviewVerdict): [number, string] {
  return [v.severity === "critical" ? 0 : 1, v.verdict_id ?? ""];
}

/** bbox 있는 verdict의 image 집합(등장 순서 보존). */
export function highlightImages(verdicts: ReviewVerdict[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const v of verdicts) {
    const img = v.location?.image;
    if (img && v.location?.bbox && !seen.has(img)) {
      seen.add(img);
      out.push(img);
    }
  }
  return out;
}

/** 해당 image의 bbox verdict를 정규 정렬해 verdict_id→핀번호(1..N) 매핑. */
export function numberedForImage(verdicts: ReviewVerdict[], image: string): Map<string, number> {
  const hits = verdicts
    .filter((v) => v.location?.image === image && v.location?.bbox)
    .sort((a, b) => {
      const [sa, ia] = pinSortKey(a);
      const [sb, ib] = pinSortKey(b);
      return sa - sb || ia.localeCompare(ib);
    });
  const m = new Map<string, number>();
  hits.forEach((v, i) => {
    if (v.verdict_id) m.set(v.verdict_id, i + 1);
  });
  return m;
}
