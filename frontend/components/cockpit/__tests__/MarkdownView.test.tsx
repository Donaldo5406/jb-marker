import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { MarkdownView } from "@/components/cockpit/MarkdownView";

describe("MarkdownView 코드 강조", () => {
  it("펜스 코드블록에 hljs 토큰 강조가 적용된다", () => {
    const md = "```json\n{ \"role\": \"cta\" }\n```";
    const { container } = render(<MarkdownView content={md} />);
    expect(container.querySelector("code.hljs")).toBeTruthy();
    expect(container.querySelector("span.hljs-attr, span.hljs-string")).toBeTruthy();
  });

  it("인라인 코드는 칩 배경 스타일을 유지한다", () => {
    const { container } = render(<MarkdownView content={"본문 `inline` 코드"} />);
    const code = container.querySelector("code");
    expect(code?.className).toContain("bg-surface-container-high");
  });

  it("언어 없는 펜스 코드블록도 크래시 없이 내용을 렌더한다(graceful)", () => {
    const md = "```\nplain text, no language\n```";
    const { container } = render(<MarkdownView content={md} />);
    expect(container.querySelector("code")).toBeTruthy();
    expect(container.textContent).toContain("plain text, no language");
  });
});

describe("MarkdownView 문서형 타이포", () => {
  it("h2=22px·bold, 본문 p=15px, strong=bold", () => {
    const { container } = render(<MarkdownView content={"## 제목\n\n본문 **굵게** 끝"} />);
    const h2 = container.querySelector("h2");
    expect(h2?.className).toContain("text-[22px]");
    expect(h2?.className).toContain("font-bold");
    const p = container.querySelector("p");
    expect(p?.className).toContain("text-[15px]");
    const strong = container.querySelector("strong");
    expect(strong?.className).toContain("font-bold");
  });
});
