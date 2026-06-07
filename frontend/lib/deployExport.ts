import { api, authedFetch, type VfsNode } from "@/lib/api";

export type ExportCategory = "visual" | "report" | "verdict" | "package";
export type ExportItem = { rest: string; name: string; category: ExportCategory };
export type ExportManifest = {
  run_id: string;
  title: string | null;
  generated_at: string;
  channels: string[];
  eligibility: { total: number; eligible_count: number; excluded_count: number } | null;
  review_gate: { status: string; critical: number; warning: number } | null;
  files: string[];
};

const RULES: { re: RegExp; category: ExportCategory }[] = [
  { re: /^design\/final\/[^/]+\/[^/]+\.(png|jpe?g)$/i, category: "visual" },
  { re: /^design\/.*\/visual\/[^/]+\.(png|jpe?g)$/i, category: "visual" },
  { re: /^review\/report\.md$/i, category: "report" },
  { re: /^review\/(legal|i18n)\/[^/]+\/verdict\.json$/i, category: "verdict" },
  { re: /^deploy\/packages\/[^/]+\/.+$/i, category: "package" },
];

/** node.path를 `/{runId}/` 정규화(FileTree.buildTree와 동일 규칙) → rest 경로. */
function toRest(runId: string, path: string): string {
  const prefix = `/${runId}/`;
  return path.startsWith(prefix) ? path.slice(prefix.length) : path.replace(/^\/+/, "");
}

function baseName(rest: string): string {
  const segs = rest.split("/").filter(Boolean);
  return segs[segs.length - 1] ?? rest;
}

/** VFS 노드 트리에서 export 대상 산출물만 골라낸다(워크트리 파서). 순수 함수. */
export function collectExportItems(runId: string, nodes: VfsNode[]): ExportItem[] {
  const out: ExportItem[] = [];
  const seen = new Set<string>();
  for (const node of nodes) {
    const rest = toRest(runId, node.path);
    if (!rest || seen.has(rest)) continue;
    for (const { re, category } of RULES) {
      if (re.test(rest)) {
        out.push({ rest, name: baseName(rest), category });
        seen.add(rest);
        break;
      }
    }
  }
  return out;
}

/** export 매니페스트 구성. 순수 함수(generated_at은 호출자 주입 — 테스트 결정성). */
export function buildCampaignManifest(args: {
  runId: string;
  title: string | null;
  generatedAt: string;
  channels: string[];
  eligibility: ExportManifest["eligibility"];
  reviewGate: ExportManifest["review_gate"];
  items: ExportItem[];
}): ExportManifest {
  return {
    run_id: args.runId,
    title: args.title,
    generated_at: args.generatedAt,
    channels: args.channels,
    eligibility: args.eligibility,
    review_gate: args.reviewGate,
    files: args.items.map((i) => i.rest),
  };
}

type FetchImpl = (url: string) => Promise<{ ok: boolean; blob: () => Promise<Blob> }>;
type ZipLike = {
  file: (name: string, data: Blob | string) => void;
  generateAsync: (opts: { type: "blob" }) => Promise<Blob>;
};

/** export 대상을 ZIP 1개로 묶는다. fetch/JSZip 주입 가능(테스트). JSZip은 동적 import. */
export async function buildCampaignZip(
  runId: string,
  items: ExportItem[],
  manifest: ExportManifest,
  opts: { fetchImpl?: FetchImpl; makeZip?: () => ZipLike | Promise<ZipLike> } = {},
): Promise<Blob> {
  const fetchImpl: FetchImpl = opts.fetchImpl ?? ((url) => authedFetch(url));
  const makeZip =
    opts.makeZip ??
    (async () => {
      const mod = await import("jszip");
      const JSZip = (mod as unknown as { default?: new () => ZipLike }).default ?? (mod as unknown as new () => ZipLike);
      return new JSZip();
    });
  const zip = await makeZip();
  zip.file("manifest.json", JSON.stringify(manifest, null, 2));
  for (const item of items) {
    try {
      const res = await fetchImpl(api.assetUrl(runId, item.rest));
      if (!res.ok) continue;
      const blob = await res.blob();
      zip.file(item.rest, blob);
    } catch {
      /* 개별 파일 실패 — skip */
    }
  }
  return zip.generateAsync({ type: "blob" });
}

/** 브라우저 다운로드 트리거. */
export function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
