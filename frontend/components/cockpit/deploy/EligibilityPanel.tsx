"use client";

/** EligibilityPanel (M6 T21) — D1 발송 적법성 요약. 총·대상·제외 카운터 + 24시간 캘린더. */
type Props = {
  total: number;
  eligibleCount: number;
  excludedCount: number;
  calendar: { hour: number; blocked: boolean }[];
};

export function EligibilityPanel({ total, eligibleCount, excludedCount, calendar }: Props) {
  return (
    <div className="space-y-3" data-testid="eligibility-panel">
      <div className="flex gap-4">
        <div>
          <span className="text-gray-500 text-sm">총</span>{" "}
          <span className="font-bold text-lg">{total}</span>
        </div>
        <div>
          <span className="text-green-700 text-sm">발송대상</span>{" "}
          <span className="font-bold text-lg text-green-700">{eligibleCount}</span>
        </div>
        <div>
          <span className="text-red-700 text-sm">제외</span>{" "}
          <span className="font-bold text-lg text-red-700">{excludedCount}</span>
        </div>
      </div>
      <div>
        <div className="text-xs text-gray-500 mb-1">24시간 캘린더 (회색=차단)</div>
        <div className="grid grid-cols-12 sm:grid-cols-24 gap-px">
          {calendar.map((c) => (
            <div
              key={c.hour}
              data-blocked={c.blocked}
              className={
                "h-6 text-[10px] text-center leading-6 " +
                (c.blocked ? "bg-gray-400 text-white" : "bg-green-200")
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
