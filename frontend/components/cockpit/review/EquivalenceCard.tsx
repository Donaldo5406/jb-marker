"use client";

import { SeverityBadge } from "../SeverityBadge";
import type { ReviewVerdict } from "@/lib/reviewArtifacts";

const KIND_LABEL: Record<string, string> = {
  missing_disclosure: "필수고지 누락",
  exaggeration: "과장·추가 표현",
  mistranslation: "오역",
  omission: "누락",
};

/** R2 다국어 동등성 차이 카드. */
export function EquivalenceCard({ v }: { v: ReviewVerdict }) {
  const level = v.severity === "critical" ? "critical" : "warning";
  return (
    <div className="space-y-2 rounded-lg border border-outline-variant bg-surface-container-lowest p-4">
      <div className="flex items-center gap-2">
        <SeverityBadge level={level}>{v.severity === "critical" ? "치명" : "경고"}</SeverityBadge>
        <span className="text-caption text-on-surface-variant">
          {v.lang ?? "-"} · {(v.kind && KIND_LABEL[v.kind]) ?? v.kind ?? "차이"}
        </span>
      </div>
      {v.evidence && <p className="text-body-sm text-on-surface">{v.evidence}</p>}
      {v.disclosure && (
        <div className="rounded-md border-l-2 border-outline bg-surface-container-low px-3 py-2 text-caption text-on-surface-variant">
          필수고지: <span className="text-on-surface">{v.disclosure}</span>
        </div>
      )}
    </div>
  );
}
