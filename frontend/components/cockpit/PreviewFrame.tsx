"use client";

import * as React from "react";

import { api } from "@/lib/api";

export type PreviewFrameProps = { runId: string };

/** design-system 프리뷰 — 백엔드 self-contained HTML을 iframe srcdoc에 주입.
 *  srcdoc은 별도 문서라 JWT를 못 싣지만, HTML 내 이미지가 base64 인라인이라 무관. */
export function PreviewFrame({ runId }: PreviewFrameProps) {
  const [html, setHtml] = React.useState<string | null>(null);
  const [error, setError] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    setError(false);
    setHtml(null);
    api
      .getPreviewHtml(runId)
      .then((h) => {
        if (!cancelled) setHtml(h);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [runId]);

  if (error) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-outline-variant bg-surface-container-lowest text-body-sm text-on-surface-variant">
        프리뷰를 불러오지 못했습니다.
      </div>
    );
  }
  if (html === null) {
    return (
      <div className="h-64 animate-pulse rounded-xl border border-outline-variant bg-surface-container-high" />
    );
  }
  return (
    <iframe
      title="design-system-preview"
      srcDoc={html}
      sandbox="allow-same-origin"
      className="h-[28rem] w-full rounded-xl border border-outline-variant bg-white"
    />
  );
}
