"use client";

import { SeverityBadge } from "../SeverityBadge";
import type { ReviewVerdict } from "@/lib/reviewArtifacts";

const KIND_LABEL: Record<string, string> = {
  missing_disclosure: "필수고지 누락",
  exaggeration: "과장·추가 표현",
  mistranslation: "오역",
  omission: "누락",
};

/** R2 다국어 동등성 차이 카드. pin이 있으면 하이라이트 포스터 번호와 대응하는 핀 배지를 표시. */
export function EquivalenceCard({ v, pin }: { v: ReviewVerdict; pin?: number }) {
  const level = v.severity === "critical" ? "critical" : "warning";
  return (
    <div className="relative space-y-2 rounded-lg border border-outline-variant bg-surface-container-lowest p-4">
      {pin != null && (
        <span className={`absolute -left-3 top-4 flex h-6 w-6 items-center justify-center rounded-full text-caption font-bold text-white ${level === "critical" ? "bg-severity-critical-fg" : "bg-severity-warning-fg"}`}>{pin}</span>
      )}
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
