"use client";

import * as React from "react";

import { api } from "@/lib/api";

export type PreviewFrameProps = { runId: string };

/** 미리보기 프레임 셸 — 중립 윈도우 닷 + 라벨을 단 "디자인 시스템 미리보기" 창. */
function Shell({ children }: { children: React.ReactNode }) {
  return (
    <figure className="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest shadow-ambient">
      <figcaption className="flex items-center gap-2 border-b border-outline-variant/60 bg-surface-container-low/60 px-3 py-2">
        <span className="flex items-center gap-1.5" aria-hidden>
          <span className="h-2 w-2 rounded-full bg-outline-variant" />
          <span className="h-2 w-2 rounded-full bg-outline-variant" />
          <span className="h-2 w-2 rounded-full bg-outline-variant" />
        </span>
        <span className="text-caption text-on-surface-variant">디자인 시스템 미리보기</span>
      </figcaption>
      {children}
    </figure>
  );
}

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
      <Shell>
        <div className="flex h-64 items-center justify-center bg-surface-container-lowest text-body-sm text-on-surface-variant">
          프리뷰를 불러오지 못했습니다.
        </div>
      </Shell>
    );
  }
  if (html === null) {
    return (
      <Shell>
        <div className="h-[28rem] bg-surface-container-high motion-safe:animate-pulse" />
      </Shell>
    );
  }
  return (
    <Shell>
      <iframe
        title="design-system-preview"
        srcDoc={html}
        sandbox="allow-same-origin"
        className="h-[28rem] w-full bg-white"
      />
    </Shell>
  );
}
