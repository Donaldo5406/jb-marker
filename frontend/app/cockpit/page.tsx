"use client";

import { CockpitProvider, useCockpit } from "@/components/cockpit/CockpitProvider";
import { Sidebar } from "@/components/cockpit/Sidebar";
import { ProcessBar } from "@/components/cockpit/ProcessBar";
import { WorkspacePanel } from "@/components/cockpit/WorkspacePanel";
import { RunList } from "@/components/cockpit/RunList";
import { EntitlementPanel } from "@/components/cockpit/EntitlementPanel";
import { AccountPanel } from "@/components/cockpit/AccountPanel";
import { MockModePanel } from "@/components/cockpit/MockModePanel";
import { UpsellModal } from "@/components/cockpit/UpsellModal";
import { AskUserToast } from "@/components/cockpit/AskUserToast";

function CockpitInner() {
  const c = useCockpit();
  return (
    <div className="flex h-screen bg-surface text-on-surface">
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
        {c.view === "setting" && (
          <div className="flex-1 space-y-6 overflow-y-auto bg-surface px-6 py-8">
            <div className="mx-auto w-full max-w-3xl space-y-6">
              <AccountPanel />
              <MockModePanel />
              <EntitlementPanel />
            </div>
          </div>
        )}
      </div>
      <UpsellModal />
      <AskUserToast />
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
