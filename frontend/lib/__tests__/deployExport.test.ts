import { describe, it, expect, vi } from "vitest";
import { collectExportItems, buildCampaignManifest, buildCampaignZip } from "../deployExport";
import type { VfsNode } from "@/lib/api";

function node(path: string): VfsNode {
  return { path, mime: null, source: null, content_text: null, meta: {} };
}

const RUN = "r1";
const NODES: VfsNode[] = [
  node("/r1/design/final/ko/main.png"),
  node("/r1/design/final/ko/main.scene"),                       // scene 제외(비주얼 아님)
  node("/r1/design/design-system/components/visual/v1.png"),
  node("/r1/review/report.md"),
  node("/r1/review/legal/a1/verdict.json"),
  node("/r1/review/i18n/a1/verdict.json"),
  node("/r1/deploy/packages/email_ko/visual.png"),
  node("/r1/brainstorming/spec.md"),                            // 제외
  node("/r1/_state.json"),                                      // 제외
  node("design/final/vi/main.jpg"),                             // 접두 없는 rest 형태도 매치
];

describe("collectExportItems", () => {
  it("filters only deliverables", () => {
    const rests = collectExportItems(RUN, NODES).map((i) => i.rest).sort();
    expect(rests).toEqual([
      "deploy/packages/email_ko/visual.png",
      "design/design-system/components/visual/v1.png",
      "design/final/ko/main.png",
      "design/final/vi/main.jpg",
      "review/i18n/a1/verdict.json",
      "review/legal/a1/verdict.json",
      "review/report.md",
    ]);
  });
  it("assigns categories", () => {
    const items = collectExportItems(RUN, NODES);
    const cat = (r: string) => items.find((i) => i.rest === r)?.category;
    expect(cat("design/final/ko/main.png")).toBe("visual");
    expect(cat("review/report.md")).toBe("report");
    expect(cat("review/legal/a1/verdict.json")).toBe("verdict");
    expect(cat("deploy/packages/email_ko/visual.png")).toBe("package");
  });
});

describe("buildCampaignManifest", () => {
  it("captures files/channels/gate/eligibility/generated_at", () => {
    const items = collectExportItems(RUN, NODES);
    const m = buildCampaignManifest({
      runId: RUN, title: "캠페인", generatedAt: "2026-06-07T00:00:00Z",
      channels: ["email", "kakao"],
      eligibility: { total: 512, eligible_count: 469, excluded_count: 43 },
      reviewGate: { status: "WARN", critical: 0, warning: 2 },
      items,
    });
    expect(m.run_id).toBe(RUN);
    expect(m.title).toBe("캠페인");
    expect(m.generated_at).toBe("2026-06-07T00:00:00Z");
    expect(m.channels).toEqual(["email", "kakao"]);
    expect(m.eligibility?.eligible_count).toBe(469);
    expect(m.review_gate?.status).toBe("WARN");
    expect(m.files).toContain("review/report.md");
  });
});

describe("buildCampaignZip", () => {
  it("adds manifest + fetched files, skips non-ok", async () => {
    const added: string[] = [];
    const zip = {
      file: (name: string) => { added.push(name); },
      generateAsync: async () => new Blob(["zip"]),
    };
    const fetchImpl = vi.fn(async (url: string) => ({
      ok: !url.includes("report.md"),                  // report 실패 → skip
      blob: async () => new Blob(["x"]),
    }));
    const items = collectExportItems(RUN, NODES);
    const manifest = buildCampaignManifest({
      runId: RUN, title: null, generatedAt: "t", channels: [], eligibility: null, reviewGate: null, items,
    });
    const blob = await buildCampaignZip(RUN, items, manifest, { fetchImpl, makeZip: () => zip });
    expect(added).toContain("manifest.json");
    expect(added).toContain("design/final/ko/main.png");
    expect(added).not.toContain("review/report.md");
    expect(blob).toBeInstanceOf(Blob);
  });
});
