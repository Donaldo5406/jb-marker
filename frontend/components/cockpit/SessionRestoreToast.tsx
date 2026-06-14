"use client";

import * as React from "react";
import { CheckCircle2, X } from "lucide-react";
import { useCockpit } from "./CockpitProvider";

/** 세션 복원 알림 — 순수 프레젠테이션(StudioNavToast 알약 패턴). studio null이면 미렌더. */
export function SessionRestoreToastView({ studio, onClose }: { studio: string | null; onClose: () => void }) {
  if (!studio) return null;
  return (
    <div className="fixed bottom-20 left-1/2 z-30 -translate-x-1/2 animate-fade-in-up" data-testid="session-restore-toast">
      <div role="status" aria-live="polite"
        className="flex items-center gap-3 rounded-full border border-outline-variant bg-surface-container-lowest px-4 py-2.5 shadow-ambient">
        <CheckCircle2 className="h-4 w-4 shrink-0 text-primary" aria-hidden />
        <span className="text-body-sm text-on-surface">세션이 복원되었습니다 — 작업을 이어가세요.</span>
        <button type="button" aria-label="닫기" onClick={onClose}
          className="inline-flex h-6 w-6 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container-high">
          <X className="h-3.5 w-3.5" aria-hidden />
        </button>
      </div>
    </div>
  );
}

/** context 구독 컨테이너 — sessionRestoredStudio가 set되면 토스트 표시, 5s 후 자동 소멸. */
export function SessionRestoreToast() {
  const { sessionRestoredStudio, dismissSessionRestored } = useCockpit();
  React.useEffect(() => {
    if (!sessionRestoredStudio) return;
    const t = setTimeout(() => dismissSessionRestored(), 5000);
    return () => clearTimeout(t);
  }, [sessionRestoredStudio, dismissSessionRestored]);
  return <SessionRestoreToastView studio={sessionRestoredStudio} onClose={dismissSessionRestored} />;
}
