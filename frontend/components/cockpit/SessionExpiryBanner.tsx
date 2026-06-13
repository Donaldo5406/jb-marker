"use client";

import * as React from "react";
import { AlertTriangle, X } from "lucide-react";
import type { SessionUiState } from "./CockpitProvider";
import { useCockpit } from "./CockpitProvider";

function fmt(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

/** 만료 경고 배너 — 순수 프레젠테이션. expiredReason 우선, 없으면 stalled 세션의 suspend 카운트다운.
 *  둘 다 해당 없으면 미렌더. 카운트다운은 컨테이너가 1s 틱으로 재렌더해 갱신. */
export function SessionExpiryBannerView({ session, expiredReason, onKeepAlive, onDismissExpired }: {
  session: SessionUiState | undefined;
  expiredReason: string | null;
  onKeepAlive: () => void;
  onDismissExpired: () => void;
}) {
  if (expiredReason) {
    const msg = expiredReason === "retention_elapsed"
      ? "세션 보관 기간이 만료되어 복원할 수 없습니다. 새 작업으로 이어가세요."
      : "세션을 찾을 수 없습니다.";
    return (
      <div className="pointer-events-none fixed inset-x-0 bottom-6 z-40 flex justify-center px-4">
        <div role="alertdialog" className="pointer-events-auto flex w-full max-w-md items-start gap-2 rounded-2xl border border-severity-warning bg-surface-container-lowest p-4 shadow-ambient animate-fade-in-up">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-severity-warning" aria-hidden />
          <p className="flex-1 text-body-sm font-medium text-on-surface">{msg}</p>
          <button type="button" aria-label="닫기" onClick={onDismissExpired} className="text-on-surface-variant hover:text-on-surface"><X className="h-4 w-4" aria-hidden /></button>
        </div>
      </div>
    );
  }
  const now = Date.now();
  const warned = session && session.status === "active" && now >= session.warnAt;
  if (!session || !warned) return null;
  const remaining = session.suspendAt - now;
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-6 z-40 flex justify-center px-4">
      <div role="status" aria-live="polite" className="pointer-events-auto flex w-full max-w-md items-center gap-2 rounded-2xl border border-severity-warning bg-surface-container-lowest p-4 shadow-ambient animate-fade-in-up">
        <AlertTriangle className="h-4 w-4 shrink-0 text-severity-warning" aria-hidden />
        <p className="flex-1 text-body-sm font-medium text-on-surface">
          작업이 곧 일시중지됩니다 — <span className="tabular-nums">{fmt(remaining)}</span>
        </p>
        <button type="button" onClick={onKeepAlive}
          className="rounded-full bg-primary px-3 py-1.5 text-caption font-medium text-on-primary transition-colors hover:bg-primary-container">
          지금 이어서
        </button>
      </div>
    </div>
  );
}

/** context 구독 컨테이너 — 1s 틱으로 카운트다운 갱신. '지금 이어서'=resume(touch)로 세션 유지. */
export function SessionExpiryBanner() {
  const c = useCockpit();
  const [, force] = React.useState(0);
  const session = c.sessions[c.activeStudio];
  const active = !!c.sessionExpiredNotice || (session?.status === "active" && Date.now() >= (session?.warnAt ?? Infinity));
  React.useEffect(() => {
    if (!active) return;
    const t = setInterval(() => force((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, [active]);
  return <SessionExpiryBannerView
    session={session}
    expiredReason={c.sessionExpiredNotice}
    onKeepAlive={() => void c.resumeSession(c.activeStudio)}
    onDismissExpired={c.dismissSessionExpired} />;
}
