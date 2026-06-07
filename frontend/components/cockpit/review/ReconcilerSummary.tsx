"use client";

import dynamic from "next/dynamic";

const MarkdownView = dynamic(() => import("../MarkdownView").then((m) => m.MarkdownView), {
  loading: () => <div className="h-24" />,
});

/** R3 통합 종합 — report.md 본문(권장·충돌조정)을 렌더. 권장만(수정은 Design). */
export function ReconcilerSummary({ report }: { report: string | null }) {
  if (!report) return null;
  return (
    <div className="rounded-lg border border-outline-variant bg-surface-container-lowest p-4">
      <h3 className="mb-2 text-body-sm font-medium text-on-surface">통합 종합 (reconciler)</h3>
      <MarkdownView content={report} />
    </div>
  );
}
