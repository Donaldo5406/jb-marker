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
import { VideoStudio } from "./VideoStudio";
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
    const STEPS = ["기획", "디자인", "준법 검토", "발송"];
    return (
      <div className="flex flex-1 items-center justify-center bg-surface px-6">
        <div className="flex w-full max-w-lg animate-fade-in-up flex-col items-center gap-7 rounded-[28px] border border-outline-variant bg-surface-container-lowest px-10 py-12 text-center shadow-elev-2">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary text-on-primary shadow-elev-2">
            <Sparkles className="h-7 w-7" aria-hidden />
          </div>
          <div className="space-y-2">
            <h2 className="text-balance break-keep text-h3 text-on-surface">
              Marker로 첫 마케팅 작업을 시작하세요
            </h2>
            <p className="mx-auto max-w-sm text-balance break-keep text-body-sm text-on-surface-variant">
              기획부터 디자인·준법 검토·발송까지, 하나의 파이프라인으로 이어집니다.
            </p>
          </div>
          {/* 파이프라인 미리보기 — 시작 전 여정을 보여줘 빈 상태가 인터페이스를 가르치게 한다 */}
          <div className="flex flex-wrap items-center justify-center gap-2 text-caption text-on-surface-variant">
            {STEPS.map((step, i) => (
              <React.Fragment key={step}>
                {i > 0 && <span className="text-outline" aria-hidden>→</span>}
                <span className="rounded-full bg-surface-container px-3 py-1">{step}</span>
              </React.Fragment>
            ))}
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
  const isReview = c.activeStudio === "review";
  const isDeploy = c.activeStudio === "deploy";
  const isVideo = c.activeStudio === "video";

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

  // design: 자체 4-panel(VFS·캔버스·챗) 셸을 full-width로 단독 렌더(좌측 260px FileTree 그리드 미사용).
  if (isDesign) {
    return <DesignStudio />;
  }

  // video: DesignStudio와 동형의 full-width 셸을 단독 렌더.
  if (isVideo) {
    return <VideoStudio />;
  }

  // review/deploy(및 그 외): 좌측 FileTree 고정 + 스튜디오 콘텐츠(현행 유지).
  return (
    <div className="grid min-h-0 flex-1 grid-cols-[260px_1fr_360px] overflow-hidden bg-surface">
      <div className="min-h-0 overflow-hidden border-r border-outline-variant">
        <FileTree />
      </div>
      {isReview ? (
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
