"use client";

import * as React from "react";
import { Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { StepProgress, type Step } from "./StepProgress";

const STEPS: Step[] = [
  { id: "S0", label: "셋업" },
  { id: "S1", label: "Rough" },
  { id: "S2a", label: "비주얼" },
  { id: "S2b", label: "카피" },
  { id: "S2c", label: "브랜드" },
  { id: "S3", label: "Final" },
  { id: "done", label: "완료" },
];

export type DesignGate = { step: string; critic: Record<string, unknown> | null; auto_advanced: string[] };
export type PipelineRailProps = {
  step: string;
  onAdvance: () => void;
  onRegenerate: () => void;
  gate?: DesignGate | null;
  busy?: boolean;
  settingsOpen?: boolean;
  onToggleSettings?: () => void;
};

/** Design 헤더: 세그먼트 진행 바(StepProgress) + critic 배지 + 재생성/다음 + ⚙ 스킵 스코프 토글. */
export function PipelineRail({ step, onAdvance, onRegenerate, gate, busy, settingsOpen, onToggleSettings }: PipelineRailProps) {
  const gated = !!gate && gate.step === step;
  const critic = gate?.critic as { pass?: boolean; avg?: number } | null | undefined;
  return (
    <div className="flex items-center gap-3 border-b border-outline-variant bg-surface-container-low px-4 py-2.5">
      <div className="min-w-0 flex-1">
        <StepProgress steps={STEPS} currentId={step} busy={busy} />
      </div>
      {gated && critic && typeof critic.avg === "number" && (
        <span className={cn("shrink-0 rounded-full px-2 py-0.5 text-caption", critic.pass ? "bg-severity-ok-bg text-severity-ok-fg" : "bg-severity-warning-bg text-severity-warning-fg")}>
          critic {critic.avg.toFixed(1)} {critic.pass ? "통과" : "주의"}
        </span>
      )}
      {step !== "done" && (
        <div className="flex shrink-0 items-center gap-2">
          <button type="button" onClick={onRegenerate} disabled={busy}
            className="rounded-full border border-outline-variant px-3 py-1.5 text-caption text-on-surface transition-colors hover:bg-surface-container-high disabled:opacity-40">
            재생성
          </button>
          <button type="button" onClick={onAdvance} disabled={busy}
            className="rounded-full bg-primary px-3 py-1.5 text-caption font-medium text-on-primary transition-colors hover:bg-primary-container disabled:opacity-40">
            {busy ? "처리 중…" : gated ? "확정 & 다음 →" : "다음 단계 →"}
          </button>
        </div>
      )}
      <button type="button" onClick={onToggleSettings} aria-label="스킵 스코프 설정" aria-pressed={!!settingsOpen} title="자동 진행(confirm 생략) 범위"
        className={cn("inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full transition-colors", settingsOpen ? "bg-primary text-on-primary" : "text-on-surface-variant hover:bg-surface-container-high")}>
        <Settings className="h-4 w-4" aria-hidden />
      </button>
    </div>
  );
}
