"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

const STEPS: { id: string; label: string }[] = [
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
};

export function PipelineRail({ step, onAdvance, onRegenerate, gate, busy }: PipelineRailProps) {
  const idx = STEPS.findIndex((s) => s.id === step);
  const gated = !!gate && gate.step === step;
  const critic = gate?.critic as { pass?: boolean; avg?: number } | null | undefined;
  return (
    <div className="flex items-center gap-3 border-b border-outline-variant bg-surface-container-low px-4 py-2">
      <ol className="flex flex-1 items-center gap-1.5">
        {STEPS.map((s, i) => (
          <li
            key={s.id}
            className={cn(
              "rounded-full px-2.5 py-1 text-caption transition-colors",
              i < idx && "text-on-surface-variant",
              i === idx && "bg-primary text-on-primary font-medium",
              i > idx && "text-outline",
            )}
          >
            {s.label}
          </li>
        ))}
      </ol>
      {gated && critic && typeof critic.avg === "number" && (
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-caption",
            critic.pass
              ? "bg-tertiary-container text-on-tertiary-container"
              : "bg-error-container text-on-error-container",
          )}
        >
          critic {critic.avg.toFixed(1)} {critic.pass ? "통과" : "주의"}
        </span>
      )}
      {gated && gate && gate.auto_advanced.length > 0 && (
        <span className="text-caption text-on-surface-variant">
          자동 진행: {gate.auto_advanced.join(", ")}
        </span>
      )}
      {step !== "done" && (
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onRegenerate}
            disabled={busy}
            className="rounded-full border border-outline-variant px-3 py-1.5 text-caption text-on-surface hover:bg-surface-container-high disabled:opacity-40"
          >
            재생성
          </button>
          <button
            type="button"
            onClick={onAdvance}
            disabled={busy}
            className="rounded-full bg-primary px-3 py-1.5 text-caption font-medium text-on-primary hover:bg-primary-container disabled:opacity-40"
          >
            {busy ? "처리 중…" : gated ? "확정 & 다음 →" : "다음 단계 →"}
          </button>
        </div>
      )}
    </div>
  );
}
