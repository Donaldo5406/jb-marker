import { api, type VfsNode } from "@/lib/api";

export type ReviewVerdict = {
  verdict_id?: string;
  node: "legal" | "i18n" | "controversy";
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
  const targets = nodes.filter((n) => /\/review\/(legal|i18n|controversy)\/[^/]+\/verdict\.json$/.test(n.path));
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
  // 주 시각근거는 ko(발표 언어) 합성 렌더 → v1 → 기타 순 — verdict 적재 순서(트리
  // 알파벳순: i18n reason_*이 legal보다 앞)에 끌려 vi/zh 포스터가 첫 화면이 되는
  // 문제를 막는다(2026-07-05). sort는 stable — 같은 급 내 기존 순서 보존.
  const rank = (p: string) =>
    /_render\/ko\.png$/.test(p) ? 0 : /\/v1\.png$/.test(p) ? 1 : /_render\//.test(p) ? 2 : 3;
  return out.sort((a, b) => rank(a) - rank(b));
}

/** 해당 image의 bbox verdict를 정규 정렬해 verdict_id→핀번호(1..N) 매핑. */
export function numberedForImage(verdicts: ReviewVerdict[], image: string): Map<string, number> {
  const hits = verdicts
    .filter((v) => v.location?.image === image && v.location?.bbox)
    .sort((a, b) => {
      const [sa, ia] = pinSortKey(a);
      const [sb, ib] = pinSortKey(b);
      // 코드포인트 비교(백엔드 pin_sort_key의 Python `<`와 동일 계약).
      // localeCompare는 ICU 콜레이션이라 로케일에 따라 결과가 갈릴 수 있어
      // 백엔드(코드포인트)와 프론트 핀 번호가 어긋날 위험이 있다 — 원시 비교로 고정.
      return sa - sb || (ia < ib ? -1 : ia > ib ? 1 : 0);
    });
  const m = new Map<string, number>();
  hits.forEach((v, i) => {
    if (v.verdict_id) m.set(v.verdict_id, i + 1);
  });
  return m;
}
