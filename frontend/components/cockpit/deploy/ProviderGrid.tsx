"use client";

/** ProviderGrid (M6 T20) — 6 채널 그리드. priority 순 정렬·다중 토글·stub/live 배지. */
export type ProviderEntry = {
  id: string;
  name: string;
  logo_path: string;
  channel_type: string;
  adapter_status: "stub" | "live";
  priority: number;
};

type Props = {
  providers: ProviderEntry[];
  selected: string[];
  onChange: (next: string[]) => void;
};

export function ProviderGrid({ providers, selected, onChange }: Props) {
  const toggle = (id: string) => {
    onChange(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  };

  return (
    <div className="grid grid-cols-3 gap-3" data-testid="provider-grid">
      {[...providers]
        .sort((a, b) => a.priority - b.priority)
        .map((p) => {
          const isSel = selected.includes(p.id);
          return (
            <button
              key={p.id}
              type="button"
              data-testid={`provider-${p.id}`}
              data-selected={isSel}
              onClick={() => toggle(p.id)}
              className={
                "flex flex-col items-center gap-2 rounded-xl border p-3 transition-colors " +
                (isSel
                  ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                  : "border-outline-variant hover:bg-surface-container-high")
              }
            >
              <img src={p.logo_path} alt={p.name} className="h-10 w-10" />
              <div className="text-body-sm font-medium text-on-surface">{p.name}</div>
              <div className="flex flex-wrap justify-center gap-1">
                <span className="rounded-full bg-surface-container-high px-1.5 py-0.5 text-caption text-on-surface-variant">
                  {p.channel_type}
                </span>
                <span
                  className={
                    "rounded-full px-1.5 py-0.5 text-caption " +
                    (p.adapter_status === "stub"
                      ? "bg-severity-warning-bg text-severity-warning-fg"
                      : "bg-severity-ok-bg text-severity-ok-fg")
                  }
                >
                  {p.adapter_status}
                </span>
              </div>
            </button>
          );
        })}
    </div>
  );
}
