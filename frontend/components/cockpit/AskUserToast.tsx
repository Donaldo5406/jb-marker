"use client";

import * as React from "react";
import { MessageCircleQuestion, X } from "lucide-react";
import type { AskPayload } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useCockpit } from "./CockpitProvider";

export function AskUserToastView({ ask, onSelect, onClose }: {
  ask: AskPayload | null; onSelect: (choice: string) => void; onClose: () => void;
}) {
  if (!ask) return null;
  const tone = ask.trigger === "c" ? "border-amber-400" : "border-outline-variant";
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-6 z-30 flex justify-center px-4">
      <div className={cn("pointer-events-auto w-full max-w-md rounded-2xl border bg-surface-container-lowest p-4 shadow-ambient animate-fade-in-up", tone)}>
        <div className="flex items-start gap-2">
          <MessageCircleQuestion className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
          <p className="flex-1 text-body-sm font-medium text-on-surface">{ask.question}</p>
          <button type="button" onClick={onClose} aria-label="닫기"
            className="text-on-surface-variant hover:text-on-surface"><X className="h-4 w-4" /></button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2 pl-6">
          {ask.options.map((opt) => (
            <button key={opt} type="button" onClick={() => onSelect(opt)}
              className="rounded-full bg-primary px-3 py-1.5 text-caption font-medium text-on-primary transition-colors hover:bg-primary-container">
              {opt}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export function AskUserToast() {
  const c = useCockpit();
  return <AskUserToastView ask={c.pendingAsk} onSelect={(choice) => void c.answerAsk(choice)} onClose={c.closeAsk} />;
}
