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
                "border rounded p-3 flex flex-col items-center gap-2 transition-colors " +
                (isSel ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:bg-gray-50")
              }
            >
              <img src={p.logo_path} alt={p.name} className="w-12 h-12" />
              <div className="text-sm font-medium">{p.name}</div>
              <div className="flex gap-1 text-xs">
                <span className="px-1 bg-gray-100 rounded">{p.channel_type}</span>
                <span
                  className={
                    "px-1 rounded " +
                    (p.adapter_status === "stub"
                      ? "bg-yellow-100 text-yellow-800"
                      : "bg-green-100 text-green-800")
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
