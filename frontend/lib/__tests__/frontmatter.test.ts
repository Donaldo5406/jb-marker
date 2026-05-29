import { describe, it, expect } from "vitest";
import { splitFrontmatter } from "../frontmatter";

describe("splitFrontmatter", () => {
  it("frontmatter가 없으면 원문을 body로 반환", () => {
    const { frontmatter, body } = splitFrontmatter("# 제목\n본문");
    expect(frontmatter).toBeNull();
    expect(body).toBe("# 제목\n본문");
  });

  it("최상위 key: value만 추출하고 본문을 분리", () => {
    const md = "---\ngoal: 신규 적금 캠페인\nlanguages: [ko, en]\n---\n## 개요\n내용";
    const { frontmatter, body } = splitFrontmatter(md);
    expect(frontmatter).not.toBeNull();
    expect(frontmatter!.entries).toEqual([
      { key: "goal", value: "신규 적금 캠페인" },
      { key: "languages", value: "[ko, en]" },
    ]);
    expect(body).toBe("## 개요\n내용");
  });

  it("중첩(들여쓴) 라인은 최상위 키로 잡지 않음", () => {
    const md = "---\nfactsheet:\n  rate: 3.5\n  term: 12m\ntone: 신뢰감\n---\nbody";
    const { frontmatter } = splitFrontmatter(md);
    expect(frontmatter!.entries.map((e) => e.key)).toEqual(["factsheet", "tone"]);
  });
});
