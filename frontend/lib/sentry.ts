// Sentry 클라이언트 — DSN 없으면 전부 no-op (spec 2026-06-12 §5).
// @sentry/nextjs 불채택: Next 14.2는 withSentryConfig 빌드 래퍼 필요 → 빌드 무영향 원칙 위배.
import * as Sentry from "@sentry/browser";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
let inited = false;

export function initSentry(): void {
  if (!dsn || inited) return;
  Sentry.init({ dsn });
  inited = true;
}

/** run 화면이 run_id를 알게 된 시점에 호출 — 이후 모든 에러에 태그 자동 부착. */
export function setRunTag(runId: string): void {
  if (!dsn || !inited) return;
  Sentry.setTag("run_id", runId);
}
