"use client";

import { SeverityBadge, type SeverityLevel } from "../SeverityBadge";
import type { ReviewGate } from "@/lib/api";
import type { ReviewVerdict } from "@/lib/reviewArtifacts";

export type PreDeployReviewProps = {
  designDone: boolean;
  gate: ReviewGate | null;
  verdicts: ReviewVerdict[];
};

const GATE_LEVEL: Record<string, SeverityLevel> = { PASS: "ok", WARN: "warning", BLOCKED: "critical" };

/** 배포 전 검토 요약 — Design 완료 + 법령/i18n 게이트 + 위반 칩. */
export function PreDeployReview({ designDone, gate, verdicts }: PreDeployReviewProps) {
  const notReviewed = !gate && verdicts.length === 0;

  const count = (node: "legal" | "i18n" | "controversy", sev: "critical" | "warning") =>
    verdicts.filter((vd) => vd.node === node && vd.severity === sev).length;
  const legalCritical = count("legal", "critical");
  const legalWarning = count("legal", "warning");
  const i18nCritical = count("i18n", "critical");
  const i18nWarning = count("i18n", "warning");
  const i18nTotal = i18nCritical + i18nWarning;
  const controversyCritical = count("controversy", "critical");
  const controversyWarning = count("controversy", "warning");
  const controversyTotal = controversyCritical + controversyWarning;
  const totalViolations = legalCritical + legalWarning + i18nTotal + controversyTotal;

  const gateLevel: SeverityLevel = (gate?.status && GATE_LEVEL[gate.status]) || "info";

  if (notReviewed) {
    return (
      <div data-testid="predeploy-review" className="space-y-2">
        <SeverityBadge level="info">검토 미실행</SeverityBadge>
        <p className="text-caption text-on-surface-variant">
          Review 스튜디오에서 검토를 먼저 실행하면 적법성·등가성 결과가 여기 요약됩니다.
        </p>
      </div>
    );
  }

  return (
    <div data-testid="predeploy-review" className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <SeverityBadge level={designDone ? "ok" : "info"}>Design {designDone ? "완료" : "대기"}</SeverityBadge>
        <SeverityBadge level={legalCritical ? "critical" : legalWarning ? "warning" : gateLevel}>
          법령 {gate?.status ?? "—"}
        </SeverityBadge>
        <SeverityBadge level={i18nCritical ? "critical" : i18nTotal ? "warning" : "ok"}>
          i18n {i18nTotal ? `위반 ${i18nTotal}` : "통과"}
        </SeverityBadge>
        <SeverityBadge level={controversyCritical ? "critical" : controversyTotal ? "warning" : "ok"}>
          논란 {controversyTotal ? `위반 ${controversyTotal}` : "통과"}
        </SeverityBadge>
      </div>

      {totalViolations > 0 && (
        <div className="flex flex-wrap gap-1.5" data-testid="violation-chips">
          {legalCritical > 0 && <SeverityBadge level="critical">법령 critical {legalCritical}</SeverityBadge>}
          {legalWarning > 0 && <SeverityBadge level="warning">법령 warning {legalWarning}</SeverityBadge>}
          {i18nCritical > 0 && <SeverityBadge level="critical">i18n critical {i18nCritical}</SeverityBadge>}
          {i18nWarning > 0 && <SeverityBadge level="warning">i18n warning {i18nWarning}</SeverityBadge>}
          {controversyCritical > 0 && <SeverityBadge level="critical">논란 critical {controversyCritical}</SeverityBadge>}
          {controversyWarning > 0 && <SeverityBadge level="warning">논란 warning {controversyWarning}</SeverityBadge>}
        </div>
      )}

      {gate && (
        <p className="text-caption text-on-surface-variant">
          통합 게이트 — critical {gate.critical} · warning {gate.warning}
        </p>
      )}
    </div>
  );
}
