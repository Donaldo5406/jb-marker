"use client";

import * as React from "react";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useCockpit } from "./CockpitProvider";
import { FileTree } from "./FileTree";
import { EditorPane } from "./EditorPane";
import { ChatPane } from "./ChatPane";
import { DesignStudio } from "./DesignStudio";
import { StudioPlaceholder } from "./StudioPlaceholder";

/** Workspace 본문. runId/activeStudio로 분기:
 *  - runId===null            → Start 카드("Use Marker"로 run 시작)
 *  - brainstorming           → IDE 3분할(FileTree / EditorPane / ChatPane) 실동작
 *  - design/review/deploy     → 동일 셸이되 중앙·우측은 StudioPlaceholder(FileTree 유지) */
export function WorkspacePanel() {
  const c = useCockpit();
  const [starting, setStarting] = React.useState(false);

  if (c.runId === null) {
    const start = async () => {
      setStarting(true);
      try {
        await c.startRun();
      } finally {
        setStarting(false);
      }
    };
    return (
      <div className="flex flex-1 items-center justify-center bg-surface px-6">
        <div className="flex max-w-md animate-fade-in-up flex-col items-center gap-5 rounded-[24px] border border-outline-variant bg-surface-container-lowest p-10 text-center shadow-ambient">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-on-primary">
            <Sparkles className="h-6 w-6" aria-hidden />
          </div>
          <div className="space-y-1.5">
            <h2 className="text-h3 text-on-surface">Use Marker로 첫 작업을 시작하세요</h2>
            <p className="text-body-sm text-on-surface-variant">
              파이프라인을 시작하면 brainstorming 스튜디오가 열리고, 챗으로 산출물을 만들 수 있습니다.
            </p>
          </div>
          <Button variant="primary" size="lg" onClick={start} disabled={starting}>
            {starting ? "시작 중…" : "Use Marker"}
          </Button>
        </div>
      </div>
    );
  }

  const isBrain = c.activeStudio === "brainstorming";
  const isDesign = c.activeStudio === "design";

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[260px_1fr_360px] overflow-hidden">
      {/* 좌: FileTree(모든 스튜디오에서 유지) */}
      <div className="min-h-0 overflow-hidden border-r border-outline-variant">
        <FileTree />
      </div>
      {/* 중·우: brain=Editor+Chat / design=DesignStudio(2분할 직접 방출) / 그외=Placeholder */}
      {isBrain ? (
        <>
          <div className="min-h-0 overflow-hidden border-r border-outline-variant">
            <EditorPane />
          </div>
          <div className="min-h-0 overflow-hidden">
            <ChatPane />
          </div>
        </>
      ) : isDesign ? (
        <DesignStudio />
      ) : (
        <>
          <div className="min-h-0 overflow-hidden border-r border-outline-variant">
            <StudioPlaceholder studio={c.activeStudio} />
          </div>
          <div className="min-h-0 overflow-hidden">
            <StudioPlaceholder studio={c.activeStudio} />
          </div>
        </>
      )}
    </div>
  );
}
