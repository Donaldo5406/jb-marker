import { describe, it, expect, vi, beforeEach } from "vitest";

const vfsGet = vi.fn();
vi.mock("../api", () => ({ api: { vfsGet: (...a: any[]) => vfsGet(...a) } }));

import { loadReviewVerdicts, loadReviewReport } from "../reviewArtifacts";

beforeEach(() => vfsGet.mockReset());

const nodes = [
  { path: "/r/review/legal/law_a/verdict.json", mime: null },
  { path: "/r/review/i18n/reason_b/verdict.json", mime: null },
  { path: "/r/review/report.md", mime: null },
  { path: "/r/design/final/ko/main.scene", mime: null },
] as any;

describe("loadReviewVerdicts", () => {
  it("legal·i18n verdict.json만 로드/파싱한다", async () => {
    vfsGet.mockImplementation(async (_id: string, rest?: string) => ({
      // null-safe: vitest 2.1.9가 teardown 시 wrapper를 인자 없이 1회 더 호출하므로 rest?.를 사용
      content_text: JSON.stringify({ node: rest?.includes("legal") ? "legal" : "i18n", severity: "critical", evidence: "e", location: { slot: "title" } }),
    }));
    const v = await loadReviewVerdicts("r", nodes);
    expect(v.length).toBe(2);
    expect(v.map((x) => x.node).sort()).toEqual(["i18n", "legal"]);
  });
  it("파싱 실패는 건너뛴다", async () => {
    vfsGet.mockResolvedValue({ content_text: "not-json" });
    const v = await loadReviewVerdicts("r", nodes);
    expect(v.length).toBe(0);
  });
});

describe("loadReviewReport", () => {
  it("frontmatter를 제거한 본문을 반환", async () => {
    vfsGet.mockResolvedValue({ content_text: "---\ngate:\n  status: WARN\n---\n# 보고서\n본문" });
    const r = await loadReviewReport("r");
    expect(r).toContain("# 보고서");
    expect(r).not.toContain("status: WARN");
  });
});
