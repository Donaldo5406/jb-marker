"use client";

/** PackageMatrix (M6 T21) — D2 채널×언어 셀 그리드. ok/needs_advisor/기타 톤 분기. */
type Cell = { channel: string; lang: string; status?: string; reason?: string };
type Props = {
  cells: Cell[];
  onAskAdvisor: (channel: string, lang: string) => void;
};

export function PackageMatrix({ cells, onAskAdvisor }: Props) {
  return (
    <div className="grid grid-cols-2 gap-2" data-testid="package-matrix">
      {cells.map((c) => {
        const id = `${c.channel}_${c.lang}`;
        const tone =
          c.status === "ok"
            ? "bg-green-50 border-green-300"
            : c.status === "needs_advisor"
            ? "bg-yellow-50 border-yellow-300"
            : "bg-gray-50 border-gray-300";
        return (
          <div key={id} data-testid={`cell-${id}`} className={"border border-outline-variant rounded p-3 " + tone}>
            <div className="text-sm font-medium">
              {c.channel} / {c.lang}
            </div>
            <div className="text-xs text-gray-600">{c.status || "—"}</div>
            {c.status === "needs_advisor" && (
              <button
                type="button"
                onClick={() => onAskAdvisor(c.channel, c.lang)}
                className="mt-2 text-xs underline"
              >
                advisor 호출
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
