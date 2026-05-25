import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-11 w-full rounded bg-surface-container px-4 text-body-sm text-on-surface",
        "outline-none focus:ring-1 focus:ring-primary",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";
