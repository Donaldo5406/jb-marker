"use client";

import { SeverityBadge } from "../SeverityBadge";
import type { ReviewVerdict } from "@/lib/reviewArtifacts";

/** R1 법률 위반 근거 카드 (mvp-02 CitationCard 패턴). */
export function ViolationCard({ v }: { v: ReviewVerdict }) {
  const level = v.severity === "critical" ? "critical" : "warning";
  return (
    <div className="space-y-2 rounded-lg border border-outline-variant bg-surface-container-lowest p-4">
      <div className="flex items-center gap-2">
        <SeverityBadge level={level}>{v.severity === "critical" ? "치명" : "경고"}</SeverityBadge>
        <span className="text-caption text-on-surface-variant">
          {(v.location?.slot ?? v.asset_id ?? "자산")} · {v.lang ?? "-"}
        </span>
      </div>
      {v.evidence && <p className="text-body-sm text-on-surface">{v.evidence}</p>}
      {v.clause && (
        <div className="rounded-md border-l-2 border-outline bg-surface-container-low px-3 py-2 text-caption text-on-surface-variant">
          <span className="font-medium text-on-surface">{v.clause}</span>
          {v.official_source_url && (
            <a href={v.official_source_url} target="_blank" rel="noreferrer" className="ml-2 underline">원문</a>
          )}
        </div>
      )}
    </div>
  );
}
