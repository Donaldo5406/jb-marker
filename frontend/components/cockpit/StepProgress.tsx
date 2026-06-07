"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export type Step = { id: string; label: string };
type SegState = "done" | "active" | "pending";

/** 세그먼트 프로그레스 바(순수 표현). currentId 기준 done/active/pending.
 *  Design·Review·Deploy 공용. 액션 버튼은 호출 측이 바 옆에 둔다. */
export function StepProgress({ steps, currentId }: { steps: Step[]; currentId: string }) {
  const idx = steps.findIndex((s) => s.id === currentId);
  const stateOf = (i: number): SegState =>
    idx < 0 ? "pending" : i < idx ? "done" : i === idx ? "active" : "pending";
  const SEG: Record<SegState, string> = {
    done: "bg-primary",
    active: "bg-primary ring-2 ring-primary/30",
    pending: "bg-surface-container-high",
  };
  return (
    <div className="w-full">
      <div className="flex gap-1">
        {steps.map((s, i) => (
          <div
            key={s.id}
            data-testid={`step-seg-${s.id}`}
            data-state={stateOf(i)}
            className={cn("h-1.5 flex-1 rounded-full transition-colors", SEG[stateOf(i)])}
          />
        ))}
      </div>
      <div className="mt-1.5 flex justify-between">
        {steps.map((s, i) => (
          <span
            key={s.id}
            className={cn(
              "text-caption",
              stateOf(i) === "active"
                ? "font-medium text-on-surface"
                : stateOf(i) === "done"
                  ? "text-on-surface-variant"
                  : "text-outline",
            )}
          >
            {s.label}
          </span>
        ))}
      </div>
    </div>
  );
}
