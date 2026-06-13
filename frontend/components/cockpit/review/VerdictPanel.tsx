"use client";

import { SeverityBadge, type SeverityLevel } from "../SeverityBadge";
import { cn } from "@/lib/utils";

export type VerdictPanelProps = {
  status?: string; // PASS | WARN | BLOCKED | (pending)
  gate?: { critical: number; warning: number } | null;
  actions?: string[]; // 백엔드 status 봉투의 actions 어휘(_actions_for)
  acknowledged: boolean;
  stage: string; // R0..done
  busy?: boolean;
  onRun: () => void;
  onAck: () => void;
  onRestart: () => void;
  onBackToDesign: () => void;
};

const LEVEL: Record<string, SeverityLevel> = { PASS: "ok", WARN: "warning", BLOCKED: "critical" };

/** 우측 심의 판정 패널 — 게이트 배지·카운트 + stage 버튼(검토 시작/계속) + actions 기반 동적 버튼. */
export function VerdictPanel({ status, gate, actions, acknowledged, stage, busy, onRun, onAck, onRestart, onBackToDesign }: VerdictPanelProps) {
  const level: SeverityLevel = (status && LEVEL[status]) || "info";
  // 액션 식별자 → review 컨텍스트 핸들러/라벨/스타일. regenerate=디자인으로 복귀해 재생성.
  const ACTION: Record<string, { label: string; on: () => void; primary?: boolean }> = {
    ack: { label: "경고 확인 후 진행", on: onAck, primary: true },
    regenerate: { label: "Design으로 돌아가 수정", on: onBackToDesign },
    restart: { label: "재검토", on: onRestart },
  };
  // ack은 이미 확인했으면 숨김(중복 확인 방지). 그 외 actions는 그대로 노출.
  const acts = (actions ?? []).filter((a) => a in ACTION && !(a === "ack" && acknowledged));
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

      {/* 정보 텍스트(액션과 별개 차원) */}
      {status === "PASS" && <p className="text-caption text-severity-ok-fg">위반 없음. 배포 진입 가능.</p>}
      {status === "WARN" && acknowledged && <p className="text-caption text-severity-warning-fg">경고를 확인했습니다. 배포 진입 가능.</p>}
      {status === "BLOCKED" && <p className="text-caption text-severity-critical-fg">critical 위반으로 배포가 차단되었습니다.</p>}

      {/* 백엔드 actions 어휘 기반 동적 버튼 */}
      {acts.map((a) => {
        const { label, on, primary } = ACTION[a];
        return (
          <button key={a} type="button" data-testid={`gate-action-${a}`} onClick={on}
            className={cn("w-full rounded-lg px-3 py-2 text-body-sm font-medium",
              primary ? "bg-severity-warning text-on-primary hover:opacity-90"
                      : "border border-outline-variant text-on-surface hover:bg-surface-container-high")}>
            {label}
          </button>
        );
      })}
    </div>
  );
}
