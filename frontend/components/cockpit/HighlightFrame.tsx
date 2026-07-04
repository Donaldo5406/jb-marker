"use client";

import * as React from "react";

import { api } from "@/lib/api";

export type HighlightFrameProps = { runId: string; image: string };

/** 리뷰 포스터 하이라이트 프레임 — 백엔드 self-contained HTML을 iframe srcdoc에 주입.
 *  srcdoc은 JWT 미탑재라 이미지가 base64 인라인(PreviewFrame과 동일 제약). CSS-only 애니메이션. */
export function HighlightFrame({ runId, image }: HighlightFrameProps) {
  const [html, setHtml] = React.useState<string | null>(null);
  const [error, setError] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    setError(false);
    setHtml(null);
    api
      .getReviewHighlightHtml(runId, image)
      .then((h) => {
        if (!cancelled) setHtml(h);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [runId, image]);

  if (error) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-outline-variant bg-surface-container-lowest text-body-sm text-on-surface-variant">
        하이라이트 미리보기를 불러오지 못했습니다.
      </div>
    );
  }
  if (html === null) {
    return (
      <div className="h-[30rem] rounded-xl border border-outline-variant bg-surface-container-high motion-safe:animate-pulse" />
    );
  }
  return (
    <iframe
      title="review-highlight"
      srcDoc={html}
      sandbox="allow-same-origin"
      className="h-[30rem] w-full rounded-xl border border-outline-variant bg-[#0b0f14]"
    />
  );
}
