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

export type PipelineRailProps = {
  step: string;
  onAdvance: () => void;
  onRegenerate: () => void;
  busy?: boolean;
};

export function PipelineRail({ step, onAdvance, onRegenerate, busy }: PipelineRailProps) {
  const idx = STEPS.findIndex((s) => s.id === step);
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
            {busy ? "처리 중…" : "다음 단계 →"}
          </button>
        </div>
      )}
    </div>
  );
}
