"use client";

import { SeverityBadge, type SeverityLevel } from "../SeverityBadge";

export type VerdictPanelProps = {
  status?: string; // PASS | WARN | BLOCKED | (pending)
  gate?: { critical: number; warning: number } | null;
  acknowledged: boolean;
  stage: string; // R0..done
  busy?: boolean;
  onRun: () => void;
  onAck: () => void;
  onRestart: () => void;
  onBackToDesign: () => void;
};

const LEVEL: Record<string, SeverityLevel> = { PASS: "ok", WARN: "warning", BLOCKED: "critical" };

/** 우측 심의 판정 패널 — 게이트 배지·카운트·액션(검토/경고확인/재검토/복귀). */
export function VerdictPanel({ status, gate, acknowledged, stage, busy, onRun, onAck, onRestart, onBackToDesign }: VerdictPanelProps) {
  const level: SeverityLevel = (status && LEVEL[status]) || "info";
  return (
    <div className="space-y-3 rounded-lg border border-outline-variant bg-surface-container-lowest p-4">
      <h3 className="text-body-sm font-medium text-on-surface">심의 판정</h3>
      <div className="flex items-center gap-2">
        <SeverityBadge level={level}>{status ?? "대기"}</SeverityBadge>
        {gate && (
          <span className="text-caption text-on-surface-variant">critical {gate.critical} · warning {gate.warning}</span>
        )}
      </div>

      {(stage === "R0") && (
        <button type="button" data-testid="run-review" onClick={onRun} disabled={busy}
          className="w-full rounded-lg bg-primary px-3 py-2 text-body-sm font-medium text-on-primary hover:bg-primary-container disabled:opacity-40">
          {busy ? "검토 중…" : "검토 시작"}
        </button>
      )}
      {(stage === "R1" || stage === "R2" || stage === "R3") && (
        <button type="button" data-testid="continue-review" onClick={onRun} disabled={busy}
          className="w-full rounded-lg bg-primary px-3 py-2 text-body-sm font-medium text-on-primary hover:bg-primary-container disabled:opacity-40">
          {busy ? "검토 중…" : "검토 계속"}
        </button>
      )}

      {status === "WARN" && !acknowledged && (
        <button type="button" data-testid="ack-button" onClick={onAck}
          className="w-full rounded-lg bg-severity-warning px-3 py-2 text-body-sm font-medium text-white hover:opacity-90">
          경고 확인 후 진행
        </button>
      )}
      {status === "WARN" && acknowledged && (
        <p className="text-caption text-severity-warning-fg">경고를 확인했습니다. 배포 진입 가능.</p>
      )}
      {status === "PASS" && <p className="text-caption text-severity-ok-fg">위반 없음. 배포 진입 가능.</p>}
      {status === "BLOCKED" && (
        <div className="space-y-2">
          <p className="text-caption text-severity-critical-fg">critical 위반으로 배포가 차단되었습니다.</p>
          <button type="button" onClick={onBackToDesign}
            className="w-full rounded-lg border border-outline-variant px-3 py-2 text-body-sm text-on-surface hover:bg-surface-container-high">
            Design으로 돌아가 수정
          </button>
        </div>
      )}

      {stage === "done" && (
        <button type="button" data-testid="restart-review" onClick={onRestart}
          className="w-full rounded-lg border border-outline-variant px-3 py-2 text-body-sm text-on-surface hover:bg-surface-container-high">
          재검토
        </button>
      )}
    </div>
  );
}
