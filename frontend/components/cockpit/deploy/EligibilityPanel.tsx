"use client";

/** EligibilityPanel (M6 T21) — D1 발송 적법성 요약. 총·대상·제외 통계 타일 + 24시간 캘린더. */
type Props = {
  total: number;
  eligibleCount: number;
  excludedCount: number;
  calendar: { hour: number; blocked: boolean }[];
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

export function EligibilityPanel({ total, eligibleCount, excludedCount, calendar }: Props) {
  return (
    <div className="space-y-4" data-testid="eligibility-panel">
      <div className="grid grid-cols-3 gap-2">
        <Stat label="총 수신자" value={total} tone="neutral" />
        <Stat label="발송대상" value={eligibleCount} tone="ok" />
        <Stat label="제외" value={excludedCount} tone="critical" />
      </div>
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
