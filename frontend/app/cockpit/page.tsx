"use client";

import { CockpitProvider, useCockpit } from "@/components/cockpit/CockpitProvider";
import { Sidebar } from "@/components/cockpit/Sidebar";
import { ProcessBar } from "@/components/cockpit/ProcessBar";
import { WorkspacePanel } from "@/components/cockpit/WorkspacePanel";
import { RunList } from "@/components/cockpit/RunList";
import { EntitlementPanel } from "@/components/cockpit/EntitlementPanel";
import { UpsellModal } from "@/components/cockpit/UpsellModal";

function CockpitInner() {
  const c = useCockpit();
  return (
    <div className="flex h-screen bg-background text-on-surface">
      <Sidebar view={c.view} onView={c.setView} />
      <div className="flex flex-1 flex-col overflow-hidden">
        {c.view === "workspace" && (
          <>
            {/* D8: ProcessBar는 step_status 읽기 전용 시각화 — 탭 클릭은 자유. */}
            <ProcessBar
              stepStatus={c.manifest?.step_status ?? {}}
              active={c.activeStudio}
              onSelect={c.setStudio}
            />
            <WorkspacePanel />
          </>
        )}
        {c.view === "history" && <RunList />}
        {c.view === "setting" && <EntitlementPanel />}
      </div>
      <UpsellModal />
    </div>
  );
}

export default function CockpitPage() {
  return (
    <CockpitProvider>
      <CockpitInner />
    </CockpitProvider>
  );
}
