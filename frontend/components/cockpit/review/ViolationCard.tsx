"use client";

import { SeverityBadge } from "../SeverityBadge";
import type { ReviewVerdict } from "@/lib/reviewArtifacts";

/** R1 법률 위반 근거 카드 (mvp-02 CitationCard 패턴). pin이 있으면 하이라이트 포스터 번호와 대응하는 핀 배지를 표시. */
export function ViolationCard({ v, pin }: { v: ReviewVerdict; pin?: number }) {
  const level = v.severity === "critical" ? "critical" : "warning";
  return (
    <div className="relative space-y-2 rounded-lg border border-outline-variant bg-surface-container-lowest p-4">
      {pin != null && (
        <span className={`absolute -left-3 top-4 flex h-6 w-6 items-center justify-center rounded-full text-caption font-bold text-white ${level === "critical" ? "bg-severity-critical-fg" : "bg-severity-warning-fg"}`}>{pin}</span>
      )}
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
