"use client";

import * as React from "react";
import { Sparkles } from "lucide-react";
import { Group, Panel, Separator, useDefaultLayout } from "react-resizable-panels";
import { Button } from "@/components/ui/Button";
import { useCockpit } from "./CockpitProvider";
import { FileTree } from "./FileTree";
import { EditorPane } from "./EditorPane";
import { ChatPane } from "./ChatPane";
import { DesignStudio } from "./DesignStudio";
import { ReviewStudio } from "./ReviewStudio";
import { DeployStudio } from "./DeployStudio";
import { StudioPlaceholder } from "./StudioPlaceholder";

/** Workspace 본문. runId/activeStudio로 분기:
 *  - runId===null            → Start 카드("Use Marker"로 run 시작)
 *  - brainstorming           → IDE 3분할(FileTree / EditorPane / ChatPane) 실동작
 *  - design/review/deploy     → 동일 셸이되 중앙·우측은 StudioPlaceholder(FileTree 유지) */
export function WorkspacePanel() {
  const c = useCockpit();
  const [starting, setStarting] = React.useState(false);
  // brainstorming 3분할 너비를 localStorage에 persist(v4: autoSaveId 대체).
  // Hook은 조건부 return 이전에 무조건 호출(Rules of Hooks).
  // SSR/프리렌더 시 localStorage가 없으므로 no-op 스토리지를 주입한다
  // (useDefaultLayout의 storage 기본값이 localStorage라 undefined를 넘기면 서버에서 ReferenceError).
  const layoutStorage = React.useMemo(
    () =>
      typeof window !== "undefined"
        ? window.localStorage
        : { getItem: () => null, setItem: () => {} },
    [],
  );
  const { defaultLayout, onLayoutChanged } = useDefaultLayout({
    id: "cockpit-cols-brain",
    storage: layoutStorage,
  });

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
          <Button variant="primary" size="lg" className="text-white" onClick={start} disabled={starting}>
            {starting ? "시작 중…" : "Use Marker"}
          </Button>
        </div>
      </div>
    );
  }

  const isBrain = c.activeStudio === "brainstorming";
  const isDesign = c.activeStudio === "design";
  const isReview = c.activeStudio === "review";
  const isDeploy = c.activeStudio === "deploy";

  // brainstorming: 드래그 리사이즈 3분할(FileTree / EditorPane / ChatPane). 너비는 useDefaultLayout로 persist.
  // react-resizable-panels v4 API: Group(orientation)/Panel(defaultSize·minSize·id)/Separator(role="separator").
  if (isBrain) {
    return (
      <Group
        orientation="horizontal"
        defaultLayout={defaultLayout}
        onLayoutChanged={onLayoutChanged}
        className="min-h-0 flex-1 overflow-hidden"
      >
        <Panel id="brain-tree" defaultSize={21} minSize={14} className="min-h-0 overflow-hidden border-r border-outline-variant">
          <FileTree />
        </Panel>
        <Separator className="w-px bg-outline-variant transition-colors data-[separator=hover]:bg-on-surface-variant data-[separator=active]:bg-on-surface-variant" />
        <Panel id="brain-editor" defaultSize={51} minSize={30} className="min-h-0 overflow-hidden border-r border-outline-variant">
          <EditorPane />
        </Panel>
        <Separator className="w-px bg-outline-variant transition-colors data-[separator=hover]:bg-on-surface-variant data-[separator=active]:bg-on-surface-variant" />
        <Panel id="brain-chat" defaultSize={28} minSize={18} className="min-h-0 overflow-hidden">
          <ChatPane />
        </Panel>
      </Group>
    );
  }

  // design/review/deploy(및 그 외): 좌측 FileTree 고정 + 스튜디오 콘텐츠(현행 3트랙 그리드 유지, 리사이즈 없음).
  // design/review/deploy 모두 col-span-2 단일 컨테이너를 방출(내부 레이아웃 자체 소유)하므로 우측 2트랙(1fr·360px)을 보존한다.
  return (
    <div className="grid min-h-0 flex-1 grid-cols-[260px_1fr_360px] overflow-hidden bg-surface">
      {/* 좌: FileTree(모든 스튜디오에서 유지) */}
      <div className="min-h-0 overflow-hidden border-r border-outline-variant">
        <FileTree />
      </div>
      {/* 중·우: design/review/deploy 모두 col-span-2 단일 컨테이너를 방출(내부 레이아웃 자체 소유) / 그외=Placeholder */}
      {isDesign ? (
        <DesignStudio />
      ) : isReview ? (
        <ReviewStudio />
      ) : isDeploy ? (
        <DeployStudio />
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
