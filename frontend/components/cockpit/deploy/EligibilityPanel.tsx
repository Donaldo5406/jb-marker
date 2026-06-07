"use client";

import type { EligibilityBreakdownItem } from "@/components/cockpit/CockpitProvider";

/** EligibilityPanel (M6 T21) — D1 발송 적법성 요약. 총·대상·제외 카운터 + 정책별 사유 분해 + 24시간 캘린더. */
type Props = {
  total: number;
  eligibleCount: number;
  excludedCount: number;
  calendar: { hour: number; blocked: boolean }[];
  breakdown?: EligibilityBreakdownItem[];
};

export function EligibilityPanel({ total, eligibleCount, excludedCount, calendar, breakdown }: Props) {
  return (
    <div className="space-y-3" data-testid="eligibility-panel">
      <div className="flex gap-4">
        <div>
          <span className="text-on-surface-variant text-sm">총</span>{" "}
          <span className="font-bold text-lg">{total}</span>
        </div>
        <div>
          <span className="text-severity-ok-fg text-sm">발송대상</span>{" "}
          <span className="font-bold text-lg text-severity-ok-fg">{eligibleCount}</span>
        </div>
        <div>
          <span className="text-severity-critical-fg text-sm">제외</span>{" "}
          <span className="font-bold text-lg text-severity-critical-fg">{excludedCount}</span>
        </div>
      </div>

      {breakdown && breakdown.length > 0 && (
        <div data-testid="eligibility-breakdown">
          <div className="text-xs text-on-surface-variant mb-1">제외 사유 (법령별)</div>
          <div className="space-y-2">
            {breakdown.map((g) => (
              <div
                key={g.policy}
                data-testid={`breakdown-${g.policy}`}
                className="rounded-lg border border-outline-variant bg-surface-container-low p-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-on-surface">{g.label}</span>
                  <span className="text-sm font-bold text-severity-critical-fg">{g.count}명</span>
                </div>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {g.reasons.map((r) => (
                    <span
                      key={r.status}
                      className="inline-flex items-center gap-1 rounded-full bg-severity-critical-bg px-2 py-0.5 text-[11px] text-severity-critical-fg"
                    >
                      {r.label}
                      <span className="font-semibold">{r.count}</span>
                    </span>
                  ))}
                </div>
                {g.citation?.quote && (
                  <p className="mt-1 text-[11px] leading-snug text-on-surface-variant">{g.citation.quote}</p>
                )}
                {g.citation?.source_url && (
                  <a
                    href={g.citation.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 inline-block text-[11px] text-primary underline underline-offset-2 break-all"
                  >
                    {[g.citation.law, g.citation.article].filter(Boolean).join(" ") || g.citation.source_url} ↗
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <div className="text-xs text-on-surface-variant mb-1">24시간 캘린더 (회색=차단)</div>
        <div className="grid grid-cols-12 sm:grid-cols-24 gap-px">
          {calendar.map((c) => (
            <div
              key={c.hour}
              data-blocked={c.blocked}
              className={
                "h-6 text-[10px] text-center leading-6 " +
                (c.blocked ? "bg-outline text-on-surface" : "bg-severity-ok-bg")
              }
            >
              {c.hour}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
