"use client";

import * as React from "react";
import { ArrowLeft, ArrowRight, X } from "lucide-react";
import { deriveNavSuggestion, type NavSignals } from "@/lib/cockpit-nav";
import { useCockpit } from "./CockpitProvider";

/** 단계 결론 시 다음(또는 복귀) 스튜디오 이동을 권유하는 토스트.
 *  자동 이동이 아닌 '권유' — 사용자가 ProcessBar로 직접 이동하는 동선은 유지. */
export function StudioNavToast() {
  const c = useCockpit();
  const signals: NavSignals = {
    brainDone: c.manifest?.step_status?.brainstorming === "done",
    designDone: c.designStep === "done",
    reviewStatus: c.manifest?.step_status?.review,
    reviewAcknowledged: c.reviewAcknowledged,
  };
  const suggestion = deriveNavSuggestion(signals, c.activeStudio);
  const [dismissed, setDismissed] = React.useState<string | null>(null);

  // 활성 스튜디오가 바뀌면 dismiss 리셋(새 맥락에서 다시 권유 가능).
  React.useEffect(() => {
    setDismissed(null);
  }, [c.activeStudio]);

  const key = suggestion ? `${c.activeStudio}:${suggestion.target}:${suggestion.direction}` : null;
  if (!suggestion || !key || dismissed === key) return null;

  const Icon = suggestion.direction === "back" ? ArrowLeft : ArrowRight;
  return (
    <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 animate-fade-in-up" data-testid="studio-nav-toast">
      <div className="flex items-center gap-3 rounded-full border border-outline-variant bg-surface-container-lowest px-4 py-2.5 shadow-ambient">
        <span className="text-body-sm text-on-surface">{suggestion.label}</span>
        <button
          type="button"
          data-testid="nav-go"
          onClick={() => {
            c.setStudio(suggestion.target);
            setDismissed(key);
          }}
          className="inline-flex items-center gap-1 rounded-full bg-primary px-3 py-1 text-caption font-medium text-on-primary transition-colors hover:bg-primary-container"
        >
          <Icon className="h-3.5 w-3.5" aria-hidden />
          이동
        </button>
        <button
          type="button"
          data-testid="nav-dismiss"
          aria-label="닫기"
          onClick={() => setDismissed(key)}
          className="inline-flex h-6 w-6 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container-high"
        >
          <X className="h-3.5 w-3.5" aria-hidden />
        </button>
      </div>
    </div>
  );
}
