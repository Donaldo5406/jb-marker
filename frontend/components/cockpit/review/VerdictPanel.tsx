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
  /** 판정 후 디자인이 바뀜(교정·재생성) — 판정이 현행이 아님을 표시(GAP8 2026-07-05). */
  stale?: boolean;
  onRun: () => void;
  onAck: () => void;
  onRestart: () => void;
  onBackToDesign: () => void;
  onProceedDeploy: () => void;
};

const LEVEL: Record<string, SeverityLevel> = { PASS: "ok", WARN: "warning", BLOCKED: "critical" };

/** 우측 심의 판정 패널 — 게이트 배지·카운트 + stage 버튼(검토 시작/계속) + actions 기반 동적 버튼. */
export function VerdictPanel({ status, gate, actions, acknowledged, stage, busy, stale, onRun, onAck, onRestart, onBackToDesign, onProceedDeploy }: VerdictPanelProps) {
  // 게이트 카운트가 0/0이면 시각상 PASS로 — 백엔드 flag(vision_skipped 등)로 WARN이 떠도
  // critical·warning 0인데 WARN 배지·'경고 확인' 액션이 뜨는 모킹 혼란을 제거한다.
  const clean = !!gate && gate.critical === 0 && gate.warning === 0;
  // stale: 교정/재생성 이후엔 BLOCKED/WARN을 그대로 두지 않는다 — '새 포스터인데 왜
  // 아직 차단?' 혼란(GAP8). 배지를 '재검토 필요'로 바꾸고 배포/확인 액션을 숨긴다.
  const effStatus = stale && gate ? "STALE" : clean ? "PASS" : status;
  const level: SeverityLevel = (effStatus && LEVEL[effStatus]) || "info";
  // 액션 식별자 → review 컨텍스트 핸들러/라벨/스타일. regenerate=디자인으로 복귀해 재생성.
  const ACTION: Record<string, { label: string; on: () => void; primary?: boolean }> = {
    ack: { label: "경고 확인 후 진행", on: onAck, primary: true },
    regenerate: { label: "리뷰 지적 반영해 재생성", on: onBackToDesign },
    restart: { label: "재검토", on: onRestart },
  };
  // ack은 실제 경고(effStatus==="WARN")가 남아 있고 미확인일 때만 — PASS(0/0)면 숨긴다.
  const acts = (actions ?? []).filter((a) => a in ACTION && !(a === "ack" && (acknowledged || effStatus !== "WARN")));
  return (
    <div className="space-y-3 rounded-lg border border-outline-variant bg-surface-container-lowest p-4">
      <h3 className="text-body-sm font-medium text-on-surface">심의 판정</h3>
      <div className="flex items-center gap-2">
        <SeverityBadge level={effStatus === "STALE" ? "warning" : level}>
          {effStatus === "STALE" ? "재검토 필요" : effStatus ?? "대기"}
        </SeverityBadge>
        {gate && effStatus !== "STALE" && (
          <span className="text-caption text-on-surface-variant">critical {gate.critical} · warning {gate.warning}</span>
        )}
      </div>
      {effStatus === "STALE" && (
        <p className="text-caption text-severity-warning-fg" data-testid="verdict-stale-note">
          디자인이 교정·변경되었습니다 — 재검토를 실행해 새 산출물을 다시 심의하세요.
        </p>
      )}

      {(stage === "R0") && (
        <button type="button" data-testid="run-review" onClick={onRun} disabled={busy}
          className="w-full rounded-lg bg-primary px-3 py-2 text-body-sm font-medium text-on-primary hover:bg-primary-container disabled:opacity-40">
          {busy ? "검토 중…" : "검토 시작"}
        </button>
      )}
      {(stage === "R1" || stage === "R2" || stage === "RC" || stage === "R3") && (
        <button type="button" data-testid="continue-review" onClick={onRun} disabled={busy}
          className="w-full rounded-lg bg-primary px-3 py-2 text-body-sm font-medium text-on-primary hover:bg-primary-container disabled:opacity-40">
          {busy ? "검토 중…" : "검토 계속"}
        </button>
      )}

      {/* 정보 텍스트(액션과 별개 차원) */}
      {effStatus === "PASS" && <p className="text-caption text-severity-ok-fg">위반 없음. 배포 진입 가능.</p>}
      {effStatus === "WARN" && acknowledged && <p className="text-caption text-severity-warning-fg">경고를 확인했습니다. 배포 진입 가능.</p>}
      {effStatus === "BLOCKED" && <p className="text-caption text-severity-critical-fg">critical 위반으로 배포가 차단되었습니다.</p>}

      {/* PASS(위반 0)·검토 완료(done) → Deploy 진입 버튼. WARN은 ack 버튼이 그 역할을 하므로
          PASS일 때만 노출(ack 없이 바로 deploy 전환 — deploy 게이트 해제는 WARN 전용). */}
      {effStatus === "PASS" && stage === "done" && (
        <button type="button" data-testid="gate-action-deploy" onClick={onProceedDeploy}
          className="w-full rounded-lg bg-primary px-3 py-2 text-body-sm font-medium text-on-primary hover:bg-primary-container">
          Deploy로 이동 →
        </button>
      )}
      {/* stale인데 백엔드 actions에 restart가 없어도 재검토 경로는 항상 열어둔다(GAP8). */}
      {effStatus === "STALE" && !acts.includes("restart") && (
        <button type="button" data-testid="gate-action-restart-stale" onClick={onRestart} disabled={busy}
          className="w-full rounded-lg bg-primary px-3 py-2 text-body-sm font-medium text-on-primary hover:bg-primary-container disabled:opacity-40">
          {busy ? "검토 중…" : "재검토"}
        </button>
      )}
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
