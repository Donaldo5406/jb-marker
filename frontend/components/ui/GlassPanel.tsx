import * as React from "react";
import { cn } from "@/lib/utils";

export function GlassPanel({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-xl border border-outline-variant/60 bg-surface-container-lowest/70 backdrop-blur-glass",
        className,
      )}
      {...props}
    />
  );
}
