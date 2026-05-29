"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { History, LayoutPanelLeft, Settings, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { useCockpit, type CockpitView } from "./CockpitProvider";
import { ConfirmToastView } from "./ConfirmToast";

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
  const router = useRouter();
  const { runId } = useCockpit();
  const [confirmOpen, setConfirmOpen] = React.useState(false);

  // 로고 클릭 → 메인('/') 이동. 활성 작업(run)이 있으면 비저장 손실 경고 토스트 후 이동.
  const goHome = () => {
    if (runId) setConfirmOpen(true);
    else router.push("/");
  };

  return (
    <>
      <aside className="flex w-16 shrink-0 flex-col items-center gap-1 border-r border-outline-variant bg-surface-container py-3">
      <button
        type="button"
        onClick={goHome}
        aria-label="메인으로"
        title="메인으로"
        className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-on-primary transition-transform hover:scale-105"
      >
        <Sparkles className="h-5 w-5" aria-hidden />
      </button>
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
      <ConfirmToastView
        open={confirmOpen}
        message="작업이 저장되지 않을 수 있습니다. 이동하시겠습니까?"
        onConfirm={() => {
          setConfirmOpen(false);
          router.push("/");
        }}
        onCancel={() => setConfirmOpen(false)}
      />
    </>
  );
}
