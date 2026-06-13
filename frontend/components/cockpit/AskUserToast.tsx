"use client";

import * as React from "react";
import { MessageCircleQuestion, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useCockpit } from "./CockpitProvider";

/** View가 기대하는 ask 모양(구 페이로드와 동형) — 봉투에서 컨테이너가 매핑해 전달. */
type AskView = { trigger: "a" | "b" | "c"; question: string; options: string[] };

export function AskUserToastView({ ask, onSelect, onClose }: {
  ask: AskView | null; onSelect: (choice: string) => void; onClose: () => void;
}) {
  if (!ask) return null;
  const tone = ask.trigger === "c" ? "border-severity-warning" : "border-outline-variant";
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-6 z-30 flex justify-center px-4">
      <div role="status" aria-live="polite" aria-labelledby="askuser-question"
        className={cn("pointer-events-auto w-full max-w-md rounded-2xl border bg-surface-container-lowest p-4 shadow-ambient animate-fade-in-up", tone)}>
        <div className="flex items-start gap-2">
          <MessageCircleQuestion className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
          <p id="askuser-question" className="flex-1 text-body-sm font-medium text-on-surface">{ask.question}</p>
          <button type="button" onClick={onClose} aria-label="닫기"
            className="text-on-surface-variant hover:text-on-surface"><X className="h-4 w-4" aria-hidden /></button>
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
  // ask 봉투(kind==="ask")를 View 기대 모양으로 명시 매핑 — 필수 필드 누락 봉투는 렌더하지 않음.
  const g = c.pendingGate;
  const ask: AskView | null =
    g?.kind === "ask" && g.question && Array.isArray(g.options) && g.options.length > 0
      // trigger는 tone(c=경고 강조)에만 쓰임 — 누락/빈값이면 "a"(기본 tone)로 폴백.
      ? { trigger: g.trigger || "a", question: g.question, options: g.options }
      : null;
  return <AskUserToastView ask={ask} onSelect={(choice) => void c.answerAsk(choice)} onClose={c.closeAsk} />;
}
