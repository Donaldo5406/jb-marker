"use client";

import { SeverityBadge } from "../SeverityBadge";
import type { ReviewVerdict } from "@/lib/reviewArtifacts";

const CATEGORY_KR: Record<string, string> = {
  disaster_memorial: "참사·사건",
  community_signal: "커뮤니티 심볼",
  community_lingo: "커뮤니티 은어",
  other_sensitive: "민감 상징",
};

/** RC 논란 리스크 근거 카드 (ViolationCard 패턴). 정치 판단이 아닌 평판 리스크 표면화. */
export function ControversyCard({ v }: { v: ReviewVerdict }) {
  const level = v.severity === "critical" ? "critical" : "warning";
  const cat = v.kind ? (CATEGORY_KR[v.kind] ?? v.kind) : "논란";
  return (
    <div className="space-y-2 rounded-lg border border-outline-variant bg-surface-container-lowest p-4">
      <div className="flex items-center gap-2">
        <SeverityBadge level={level}>{v.severity === "critical" ? "치명" : "경고"}</SeverityBadge>
        <span className="text-caption text-on-surface-variant">
          {cat} · {(v.location?.slot ?? "논란")} · {v.lang ?? "-"}
        </span>
      </div>
      {v.evidence && <p className="text-body-sm text-on-surface">{v.evidence}</p>}
      {v.official_source_url && (
        <div className="rounded-md border-l-2 border-outline bg-surface-container-low px-3 py-2 text-caption text-on-surface-variant">
          <a href={v.official_source_url} target="_blank" rel="noreferrer" className="underline">선례·근거</a>
        </div>
      )}
    </div>
  );
}
