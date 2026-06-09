import { cn } from "@/lib/utils";

export type Step = { id: string; label: string };
type SegState = "done" | "active" | "pending";

const SEG: Record<SegState, string> = {
  done: "bg-primary",
  active: "bg-primary ring-2 ring-primary/30",
  pending: "bg-surface-container-high",
};

function segState(idx: number, i: number): SegState {
  if (idx < 0) return "pending";
  if (i < idx) return "done";
  if (i === idx) return "active";
  return "pending";
}

/** 세그먼트 프로그레스 바(순수 표현). currentId 기준 done/active/pending.
 *  세그먼트 바와 라벨은 동일한 flex-1 그리드라 라벨이 각 바 중앙에 정렬된다.
 *  busy=true면 현재(active) 세그먼트에 좌→우 shimmer 애니메이션을 표시한다.
 *  Design·Review·Deploy 공용. 액션 버튼은 호출 측이 바 옆에 둔다. */
export function StepProgress({ steps, currentId, busy = false }: { steps: Step[]; currentId: string; busy?: boolean }) {
  const idx = steps.findIndex((s) => s.id === currentId);
  return (
    <div className="w-full">
      <div className="flex gap-1">
        {steps.map((s, i) => {
          const state = segState(idx, i);
          return (
            <div
              key={s.id}
              data-testid={`step-seg-${s.id}`}
              data-state={state}
              className={cn("relative h-1.5 flex-1 overflow-hidden rounded-full transition-colors", SEG[state])}
            >
              {state === "active" && busy && (
                <span
                  aria-hidden
                  className="absolute inset-y-0 left-0 w-full animate-rail-shimmer bg-gradient-to-r from-transparent via-white/70 to-transparent"
                />
              )}
            </div>
          );
        })}
      </div>
      <div className="mt-1.5 flex gap-1">
        {steps.map((s, i) => {
          const state = segState(idx, i);
          return (
            <span
              key={s.id}
              className={cn(
                "min-w-0 flex-1 truncate text-center text-caption",
                state === "active"
                  ? "font-medium text-on-surface"
                  : state === "done"
                    ? "text-on-surface-variant"
                    : "text-outline",
              )}
            >
              {s.label}
            </span>
          );
        })}
      </div>
    </div>
  );
}
