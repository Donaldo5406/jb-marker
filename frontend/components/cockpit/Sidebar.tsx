"use client";

import { History, LayoutPanelLeft, Settings, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import type { CockpitView } from "./CockpitProvider";

const ITEMS: { view: CockpitView; label: string; Icon: typeof History }[] = [
  { view: "workspace", label: "Workspace", Icon: LayoutPanelLeft },
  { view: "history", label: "History", Icon: History },
  { view: "setting", label: "Setting", Icon: Settings },
];

export type SidebarProps = {
  view: CockpitView;
  onView: (v: CockpitView) => void;
};

/** 좁은 세로 네비 바: 로고 + Workspace/History/Setting 전환. */
export function Sidebar({ view, onView }: SidebarProps) {
  return (
    <aside className="flex w-16 shrink-0 flex-col items-center gap-1 border-r border-outline-variant bg-surface-container py-3">
      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-on-primary">
        <Sparkles className="h-5 w-5" aria-label="JB Marker" />
      </div>
      {ITEMS.map(({ view: v, label, Icon }) => {
        const isActive = view === v;
        return (
          <button
            key={v}
            type="button"
            aria-label={label}
            aria-current={isActive ? "page" : undefined}
            title={label}
            onClick={() => onView(v)}
            className={cn(
              "flex h-12 w-12 flex-col items-center justify-center gap-0.5 rounded-xl text-[10px] font-medium transition-colors",
              isActive
                ? "bg-surface-container-highest text-on-surface"
                : "text-on-surface-variant hover:bg-surface-container-high",
            )}
          >
            <Icon className="h-5 w-5" aria-hidden />
            <span className="leading-none">{label}</span>
          </button>
        );
      })}
    </aside>
  );
}
