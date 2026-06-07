import { api, type VfsNode } from "@/lib/api";

export type ReviewVerdict = {
  verdict_id?: string;
  node: "legal" | "i18n";
  asset_id?: string;
  lang?: string | null;
  severity: "critical" | "warning";
  location?: { slot?: string } & Record<string, unknown>;
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
