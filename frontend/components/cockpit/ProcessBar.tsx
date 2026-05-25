"use client";

import { Check, ChevronRight, Lock } from "lucide-react";
import { cn } from "@/lib/utils";
import { STUDIOS, studioNavState, type NavStatus, type Studio } from "@/lib/cockpit-nav";

const LABELS: Record<Studio, string> = {
  brainstorming: "brainstorming",
  design: "design",
  review: "review",
  deploy: "deploy",
};

/** 단계 상태별 도트(StatusDot 토큰과 일관)·텍스트 톤. */
const DOT_TONE: Record<NavStatus, string> = {
  done: "bg-primary",
  active: "bg-primary animate-pulse",
  pending: "bg-outline-variant",
  blocked: "bg-error",
};

export type ProcessBarProps = {
  stepStatus: Record<string, string>;
  active: Studio;
  onSelect: (s: Studio) => void;
};

/**
 * 4단계 인디케이터 겸 네비게이터.
 * Deferral D8 — M2에서 ProcessBar는 `manifest.step_status`의 **읽기 전용 시각화**다.
 * 완료 판정·set_step_status 쓰기·review→deploy BLOCK 판정은 M3+ 소관.
 * 따라서 모든 탭은 자유롭게 클릭 가능(blocked 포함) — 항상 onSelect 호출.
 */
export function ProcessBar({ stepStatus, active, onSelect }: ProcessBarProps) {
  const nav = studioNavState(stepStatus);

  return (
    <nav
      aria-label="파이프라인 단계"
      className="flex items-center gap-1 border-b border-outline-variant bg-surface-container-low px-4 py-2"
    >
      {STUDIOS.map((s, i) => {
        const status = nav[s];
        const isActive = active === s;
        const blocked = status === "blocked";
        return (
          <div key={s} className="flex items-center">
            <button
              type="button"
              data-testid={`step-${s}`}
              data-status={status}
              aria-current={isActive ? "step" : undefined}
              onClick={() => onSelect(s)}
              className={cn(
                "group inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-body-sm transition-colors",
                isActive
                  ? "bg-surface-container-highest font-medium text-on-surface"
                  : "text-on-surface-variant hover:bg-surface-container",
                // D8: blocked는 잠금 '시각 표현'만 — 흐림 처리하되 클릭은 막지 않음.
                blocked && "opacity-60",
              )}
            >
              <span className="flex h-4 w-4 items-center justify-center">
                {status === "done" ? (
                  <Check className="h-3.5 w-3.5 text-primary" aria-label="완료" />
                ) : blocked ? (
                  <Lock className="h-3.5 w-3.5 text-error" aria-label="잠금" />
                ) : (
                  <span className={cn("inline-block h-2 w-2 rounded-full", DOT_TONE[status])} />
                )}
              </span>
              <span className="capitalize">{LABELS[s]}</span>
            </button>
            {i < STUDIOS.length - 1 && (
              <ChevronRight className="mx-0.5 h-4 w-4 shrink-0 text-outline" aria-hidden />
            )}
          </div>
        );
      })}
    </nav>
  );
}
