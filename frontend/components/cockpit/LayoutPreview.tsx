"use client";

import * as React from "react";

import { api } from "@/lib/api";

export type LayoutPreviewProps = {
  runId: string;
  /** 파이프라인 진행/게이트 변화 시 재fetch 트리거(폴링 없음). */
  refreshKey?: string | number;
  /** preview.html 부재(404)·로드 실패·로딩 중 표시할 폴백(부모의 기존 placeholder). */
  fallback?: React.ReactNode;
};

/** 백엔드가 결정론으로 렌더한 시안 목업 HTML의 VFS 경로(Task 2 계약). */
const PREVIEW_PATH = "design/rough/preview.html";

/** 시안 프리뷰 셸 — 상단 라벨 + iframe. PreviewFrame.tsx의 figcaption 스타일 재사용. */
function Shell({ children }: { children: React.ReactNode }) {
  return (
    <figure className="flex h-full min-h-0 flex-col overflow-hidden bg-surface">
      <figcaption className="flex items-center gap-2 border-b border-outline-variant/60 bg-surface-container-low/60 px-3 py-2">
        <span className="text-caption text-on-surface-variant">
          시안 프리뷰 — 최종 생성물과 다를 수 있습니다
        </span>
      </figcaption>
      {children}
    </figure>
  );
}

/** design/rough/preview.html(백엔드 결정론 목업)을 iframe srcdoc으로 주입.
 *  성공 시 라벨 + iframe, 로딩/실패(404 포함) 시 fallback(부모 placeholder)을 렌더한다.
 *  srcdoc은 별도 문서라 JWT를 못 싣지만, HTML 내 이미지가 base64 인라인이라 무관.
 *
 *  폴백 설계(단순안): 컴포넌트가 세 상태를 모두 소유한다 — 로딩/실패는 동일하게 fallback을,
 *  성공만 iframe을 렌더. 부모는 항상 <LayoutPreview fallback={placeholder} /> 를 렌더하면
 *  되고, "preview.html 없음" 경로에서 기존 placeholder 문구가 그대로 유지된다(회귀 없음). */
export function LayoutPreview({ runId, refreshKey, fallback = null }: LayoutPreviewProps) {
  const [html, setHtml] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    setHtml(null);
    api
      .vfsGet(runId, PREVIEW_PATH)
      .then((node) => {
        if (!cancelled) setHtml(node.content_text ?? "");
      })
      .catch(() => {
        if (!cancelled) setHtml(null);
      });
    return () => {
      cancelled = true;
    };
  }, [runId, refreshKey]);

  if (html === null) return <>{fallback}</>;
  return (
    <Shell>
      <iframe
        title="시안 프리뷰"
        srcDoc={html}
        sandbox="allow-same-origin"
        className="min-h-0 w-full flex-1 bg-white"
      />
    </Shell>
  );
}
