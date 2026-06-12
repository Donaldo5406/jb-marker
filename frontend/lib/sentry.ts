// Sentry 클라이언트 — DSN 없으면 전부 no-op (spec 2026-06-12 §5).
// @sentry/nextjs 불채택: Next 14.2는 withSentryConfig 빌드 래퍼 필요 → 빌드 무영향 원칙 위배.
// 주의: 향후 app/error.tsx 등 React error boundary 도입 시 — boundary가 삼킨 렌더 에러는
// window.onerror에 안 잡히므로 boundary에서 Sentry.captureException 명시 호출 필요.
import * as Sentry from "@sentry/browser";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
let inited = false;

export function initSentry(): void {
  if (!dsn || inited) return;
  Sentry.init({ dsn });
  inited = true;
}

/** run 화면이 run_id를 알게 된 시점에 호출 — 이후 모든 에러에 태그 자동 부착.
 * init 전 호출돼도 안전: setTag는 isolation scope(global singleton)에 쓰여 init 후 이벤트에도 적용된다. */
export function setRunTag(runId: string): void {
  if (!dsn) return;
  Sentry.setTag("run_id", runId);
}
