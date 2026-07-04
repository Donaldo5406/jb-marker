import * as React from "react";
import { cn } from "@/lib/utils";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-[24px] border border-outline-variant bg-surface-container-lowest p-8 shadow-elev-1",
        className,
      )}
      {...props}
    />
  );
}
