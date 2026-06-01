"use client";

import * as React from "react";
import hljs from "highlight.js/lib/common";
import { fileType } from "@/lib/fileType";

const MAX = 200_000; // 동기 강조의 메인스레드 점유 방지 임계.

/** .json/.ts 등 읽기 전용 코드 뷰 — highlight.js 동기 강조 + 라인넘버 거터. */
export function CodeView({ name, content }: { name: string; content: string }) {
  const lang = fileType(name).lang;
  const html = React.useMemo(() => {
    if (content.length > MAX) return null;
    const language = hljs.getLanguage(lang) ? lang : "plaintext";
    try {
      return hljs.highlight(content, { language }).value;
    } catch {
      return null;
    }
  }, [content, lang]);

  const lineCount = content.split("\n").length;
  const gutter = Array.from({ length: lineCount }, (_, i) => i + 1).join("\n");

  return (
    <div className="flex-1 overflow-auto bg-surface">
      <div className="flex min-h-full font-mono text-body-sm leading-relaxed">
        <pre aria-hidden className="select-none py-4 pl-4 pr-3 text-right text-outline">{gutter}</pre>
        {html === null ? (
          <pre className="flex-1 whitespace-pre py-4 pr-4 text-on-surface"><code>{content}</code></pre>
        ) : (
          <pre className="hljs flex-1 whitespace-pre bg-transparent py-4 pr-4">
            <code dangerouslySetInnerHTML={{ __html: html }} />
          </pre>
        )}
      </div>
    </div>
  );
}
