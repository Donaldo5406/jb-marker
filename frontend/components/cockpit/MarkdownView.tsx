"use client";

import { Fragment } from "react";
import Markdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import { splitFrontmatter } from "@/lib/frontmatter";

/** 디자인 토큰에 맞춘 마크다운 요소 매핑(@tailwindcss/typography 미사용 — 의존성 최소화).
 *  react-markdown이 넘기는 `node` prop은 DOM으로 전달하면 경고가 나므로 구조분해로 제거한다. */
const COMPONENTS: Components = {
  h1: ({ node, ...p }) => <h1 className="mb-2 mt-5 text-h3 font-semibold text-on-surface" {...p} />,
  h2: ({ node, ...p }) => <h2 className="mb-2 mt-5 text-[20px] font-semibold leading-tight text-on-surface" {...p} />,
  h3: ({ node, ...p }) => <h3 className="mb-1.5 mt-4 text-body-lg font-semibold text-on-surface" {...p} />,
  h4: ({ node, ...p }) => <h4 className="mb-1 mt-3 text-body-sm font-semibold text-on-surface" {...p} />,
  p: ({ node, ...p }) => <p className="my-2 leading-relaxed text-on-surface" {...p} />,
  ul: ({ node, ...p }) => <ul className="my-2 list-disc space-y-1 pl-5 text-on-surface" {...p} />,
  ol: ({ node, ...p }) => <ol className="my-2 list-decimal space-y-1 pl-5 text-on-surface" {...p} />,
  li: ({ node, ...p }) => <li className="leading-relaxed" {...p} />,
  a: ({ node, ...p }) => <a className="text-primary underline underline-offset-2" target="_blank" rel="noreferrer" {...p} />,
  code: ({ node, ...p }) => <code className="rounded bg-surface-container-high px-1 py-0.5 font-mono text-[0.85em] text-on-surface" {...p} />,
  pre: ({ node, ...p }) => <pre className="my-3 overflow-x-auto rounded-lg bg-surface-container-high p-3 font-mono text-body-sm text-on-surface" {...p} />,
  blockquote: ({ node, ...p }) => <blockquote className="my-3 border-l-2 border-outline pl-3 text-on-surface-variant" {...p} />,
  hr: () => <hr className="my-4 border-outline-variant" />,
  table: ({ node, ...p }) => (
    <div className="my-3 overflow-x-auto">
      <table className="w-full border-collapse text-body-sm" {...p} />
    </div>
  ),
  th: ({ node, ...p }) => <th className="border border-outline-variant bg-surface-container px-2 py-1 text-left font-medium text-on-surface" {...p} />,
  td: ({ node, ...p }) => <td className="border border-outline-variant px-2 py-1 align-top text-on-surface" {...p} />,
  strong: ({ node, ...p }) => <strong className="font-semibold text-on-surface" {...p} />,
};

/** .md Preview: frontmatter는 메타블록, 본문은 GFM 마크다운으로 렌더. rehype-sanitize로 raw HTML 차단. */
export function MarkdownView({ content }: { content: string }) {
  const { frontmatter, body } = splitFrontmatter(content);
  return (
    <div className="flex-1 overflow-y-auto bg-surface px-6 py-5">
      <div className="mx-auto max-w-3xl">
        {frontmatter && frontmatter.entries.length > 0 && (
          <dl className="mb-5 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1.5 rounded-xl border border-outline-variant bg-surface-container-lowest p-4 text-body-sm">
            {frontmatter.entries.map(({ key, value }) => (
              <Fragment key={key}>
                <dt className="font-medium text-on-surface-variant">{key}</dt>
                <dd className="min-w-0 break-words text-on-surface">{value || "—"}</dd>
              </Fragment>
            ))}
          </dl>
        )}
        <div className="markdown-body">
          <Markdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]} components={COMPONENTS}>
            {body}
          </Markdown>
        </div>
      </div>
    </div>
  );
}
