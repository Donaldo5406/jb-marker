"use client";

import type { EligibilityBreakdownItem } from "@/components/cockpit/CockpitProvider";

/** EligibilityPanel (M6 T21) — D1 발송 적법성 요약. 총·대상·제외 통계 타일 + 정책별 사유 분해 + 24시간 캘린더. */
type Props = {
  total: number;
  eligibleCount: number;
  excludedCount: number;
  calendar: { hour: number; blocked: boolean }[];
  breakdown?: EligibilityBreakdownItem[];
};

function Stat({ label, value, tone }: { label: string; value: number; tone: "neutral" | "ok" | "critical" }) {
  const color = tone === "ok" ? "text-severity-ok-fg" : tone === "critical" ? "text-severity-critical-fg" : "text-on-surface";
  return (
    <div className="rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2">
      <div className="text-caption text-on-surface-variant">{label}</div>
      <div className={"text-h3 font-bold tabular-nums " + color}>{value}</div>
    </div>
  );
}

export function EligibilityPanel({ total, eligibleCount, excludedCount, calendar, breakdown }: Props) {
  return (
    <div className="space-y-4" data-testid="eligibility-panel">
      <div className="grid grid-cols-3 gap-2">
        <Stat label="총 수신자" value={total} tone="neutral" />
        <Stat label="발송대상" value={eligibleCount} tone="ok" />
        <Stat label="제외" value={excludedCount} tone="critical" />
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
        <div className="mb-1.5 text-caption text-on-surface-variant">발송 가능 시간대 (회색 = 야간 차단 21~08)</div>
        <div className="grid grid-cols-12 gap-px sm:grid-cols-24">
          {calendar.map((c) => (
            <div
              key={c.hour}
              data-blocked={c.blocked}
              title={`${c.hour}시`}
              className={
                "h-6 text-center text-[10px] leading-6 " +
                (c.blocked ? "bg-surface-container-high text-outline" : "bg-severity-ok-bg text-severity-ok-fg")
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
