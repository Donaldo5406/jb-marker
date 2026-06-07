import * as React from "react";
import { cn } from "@/lib/utils";

export type SeverityLevel = "critical" | "warning" | "ok" | "info";

const TONE: Record<SeverityLevel, string> = {
  critical: "bg-severity-critical-bg text-severity-critical-fg",
  warning: "bg-severity-warning-bg text-severity-warning-fg",
  ok: "bg-severity-ok-bg text-severity-ok-fg",
  info: "bg-severity-info-bg text-severity-info-fg",
};

/** severity 배지 — 색 토큰의 단일 소비처(임의색 금지). */
export function SeverityBadge({
  level,
  children,
}: {
  level: SeverityLevel;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-caption font-medium",
        TONE[level],
      )}
    >
      {children}
    </span>
  );
}
