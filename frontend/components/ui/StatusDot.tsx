import { cn } from "@/lib/utils";

const tone = {
  active: "bg-primary",
  processing: "bg-secondary animate-pulse",
  error: "bg-error",
} as const;

export function StatusDot({ status, className }: { status: keyof typeof tone; className?: string }) {
  return <span className={cn("inline-block h-2 w-2 rounded-full", tone[status], className)} />;
}
