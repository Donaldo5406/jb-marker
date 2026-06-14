"use client";

import * as React from "react";
import { Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { StepProgress, type Step } from "./StepProgress";
import type { DesignGate } from "@/lib/api";
import { gateActionLabel } from "@/lib/gateActions";

const STEPS: Step[] = [
  { id: "S0", label: "셋업" },
  { id: "S1", label: "Rough" },
  { id: "S2b", label: "카피" },
  { id: "S2a", label: "비주얼" },
  { id: "S2c", label: "브랜드" },
  { id: "S3", label: "Final" },
  { id: "done", label: "완료" },
];

/** 영상 파이프라인 단계(V0~V3) — VideoStudio가 PipelineRail.steps로 주입. design STEPS와 라벨 어휘 공유. */
export const VIDEO_STEPS: Step[] = [
  { id: "V0", label: "셋업" },
  { id: "V1", label: "콘티" },
  { id: "V2a", label: "촬영" },
  { id: "V2b", label: "카피" },
  { id: "V2c", label: "브랜드" },
  { id: "V3", label: "Final" },
  { id: "done", label: "완료" },
];

export type PipelineRailProps = {
  step: string;
  steps?: Step[];
  onAdvance: () => void;
  onRegenerate: () => void;
  gate?: DesignGate | null;
  busy?: boolean;
  settingsOpen?: boolean;
  onToggleSettings?: () => void;
};

/** Design 헤더: 세그먼트 진행 바(StepProgress) + critic 배지 + 재생성/다음 + ⚙ 스킵 스코프 토글. */
export function PipelineRail({ step, steps = STEPS, onAdvance, onRegenerate, gate, busy, settingsOpen, onToggleSettings }: PipelineRailProps) {
  const gated = !!gate && gate.step === step;
  // CriticVerdict 봉투(spec §6): {passed, issues, scores?:{avg, scores}}
  const critic = gate?.critic as { passed?: boolean; scores?: { avg?: number } } | null | undefined;
  return (
    <div className="flex items-center gap-3 border-b border-outline-variant bg-surface-container-low px-4 py-2.5">
      <div className="min-w-0 flex-1">
        <StepProgress steps={steps} currentId={step} busy={busy} />
      </div>
      {gated && critic && typeof critic.scores?.avg === "number" && (
        <span className={cn("shrink-0 rounded-full px-2 py-0.5 text-caption", critic.passed ? "bg-severity-ok-bg text-severity-ok-fg" : "bg-severity-warning-bg text-severity-warning-fg")}>
          critic {critic.scores.avg.toFixed(1)} {critic.passed ? "통과" : "주의"}
        </span>
      )}
      {step !== "done" && (() => {
        // gated면 서버 선언 actions, 아니면 일반 진행 베이스라인. 순서: 재생성(좌)·primary(우).
        const acts = gated && gate?.actions?.length ? gate.actions : ["regenerate", "advance"];
        const hasRegen = acts.includes("regenerate");
        // primary는 confirm 게이트(["confirm",…])·비-gated 베이스라인(…,"advance") 양쪽에서 항상 보장됨
        // — 베이스라인에서 advance를 빼면 진행 버튼이 사라지니 유지할 것.
        const primary = acts.find((a) => a === "confirm" || a === "advance");
        return (
          <div className="flex shrink-0 items-center gap-2">
            {hasRegen && (
              <button type="button" onClick={onRegenerate} disabled={busy}
                className="rounded-full border border-outline-variant px-3 py-1.5 text-caption text-on-surface transition-colors hover:bg-surface-container-high disabled:opacity-40">
                {gateActionLabel("regenerate")}
              </button>
            )}
            {primary && (
              <button type="button" onClick={onAdvance} disabled={busy}
                className="rounded-full bg-primary px-3 py-1.5 text-caption font-medium text-on-primary transition-colors hover:bg-primary-container disabled:opacity-40">
                {busy ? "처리 중…" : gateActionLabel(primary)}
              </button>
            )}
          </div>
        );
      })()}
      <button type="button" onClick={onToggleSettings} aria-label="스킵 스코프 설정" aria-pressed={!!settingsOpen} title="자동 진행(confirm 생략) 범위"
        className={cn("inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full transition-colors", settingsOpen ? "bg-primary text-on-primary" : "text-on-surface-variant hover:bg-surface-container-high")}>
        <Settings className="h-4 w-4" aria-hidden />
      </button>
    </div>
  );
}
