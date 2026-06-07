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
            ? "border-severity-ok bg-severity-ok-bg"
            : c.status === "needs_advisor"
            ? "border-severity-warning bg-severity-warning-bg"
            : "border-outline-variant bg-surface-container-lowest";
        return (
          <div key={id} data-testid={`cell-${id}`} className={"rounded-lg border p-3 " + tone}>
            <div className="text-body-sm font-medium text-on-surface">
              {c.channel} / {c.lang}
            </div>
            <div className="text-caption text-on-surface-variant">{c.status || "—"}</div>
            {c.status === "needs_advisor" && (
              <button
                type="button"
                onClick={() => onAskAdvisor(c.channel, c.lang)}
                className="mt-2 text-caption font-medium text-primary underline"
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
