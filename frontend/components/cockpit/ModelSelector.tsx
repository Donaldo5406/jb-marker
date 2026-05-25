"use client";

import * as React from "react";
import { Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Provider } from "@/lib/api";

export type ModelChoice = {
  id: string;
  label: string;
  provider: Provider;
  isMarker: boolean;
  paid?: boolean;
};

/** Marker가 최상단(유료). 나머지는 raw 모델. provider는 gatewayRun에 그대로 전달.
 *  로컬 데모: 키 없이 동작하도록 ChatPane이 선택 provider를 그대로 보냄(fake 포함). */
export const MODELS: ModelChoice[] = [
  { id: "marker", label: "Marker", provider: "anthropic", isMarker: true, paid: true },
  { id: "claude", label: "Claude", provider: "anthropic", isMarker: false },
  { id: "gpt", label: "GPT", provider: "openai", isMarker: false },
  { id: "gemini", label: "Gemini", provider: "google", isMarker: false },
];

export type ModelSelectorProps = {
  value: string;
  onChange: (m: ModelChoice) => void;
};

/** 모델 선택 드롭다운. Marker는 'Pro' 유료 배지. */
export function ModelSelector({ value, onChange }: ModelSelectorProps) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);
  const selected = MODELS.find((m) => m.id === value) ?? MODELS.find((m) => m.provider === value);

  React.useEffect(() => {
    if (!open) return;
    const onDocClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="inline-flex items-center gap-1.5 rounded-full border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-caption font-medium text-on-surface transition-colors hover:bg-surface-container-low"
      >
        <span>{selected?.label ?? "모델 선택"}</span>
        {selected?.paid && (
          <span className="rounded-full bg-primary px-1.5 py-px text-[10px] font-semibold leading-none text-on-primary">
            Pro
          </span>
        )}
        <ChevronDown
          className={cn("h-3.5 w-3.5 text-on-surface-variant transition-transform", open && "rotate-180")}
          aria-hidden
        />
      </button>

      {open && (
        <div
          role="listbox"
          className="absolute bottom-full right-0 z-20 mb-1.5 w-44 overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest shadow-ambient animate-fade-in-up"
        >
          {MODELS.map((m) => {
            const isSel = m.id === selected?.id;
            return (
              <button
                key={m.id}
                type="button"
                role="option"
                aria-selected={isSel}
                onClick={() => {
                  onChange(m);
                  setOpen(false);
                }}
                className={cn(
                  "flex w-full items-center gap-2 px-3 py-2 text-left text-body-sm transition-colors",
                  isSel
                    ? "bg-surface-container-high text-on-surface"
                    : "text-on-surface-variant hover:bg-surface-container",
                )}
              >
                <span className="flex h-4 w-4 shrink-0 items-center justify-center">
                  {isSel && <Check className="h-3.5 w-3.5 text-primary" aria-hidden />}
                </span>
                <span className="flex-1 font-medium">{m.label}</span>
                {m.paid && (
                  <span className="rounded-full bg-primary px-1.5 py-px text-[10px] font-semibold leading-none text-on-primary">
                    Pro
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
