"use client";
import * as React from "react";
import { Group, Panel, Separator, useDefaultLayout } from "react-resizable-panels";
import { useCockpit } from "./CockpitProvider";
import { FileTree } from "./FileTree";
import { ChatPane } from "./ChatPane";
import { PipelineRail, VIDEO_STEPS } from "./PipelineRail";
import { VideoSettings } from "./VideoSettings";
import { cn } from "@/lib/utils";

const LANGS = ["ko", "en", "vi", "zh"];

/** video 탭: 상단 PipelineRail + 하단 3분할(VFS·중앙·챗). DesignStudio 미러.
 *  중앙은 P3에선 안내 플레이스홀더 — VideoEditor(라이브 프리뷰·타임라인)는 P4. */
export function VideoStudio() {
  const c = useCockpit();
  const [busy, setBusy] = React.useState(false);
  const [showSettings, setShowSettings] = React.useState(false);
  const act = async (action: string) => { setBusy(true); try { await c.runVideo(action); } finally { setBusy(false); } };
  const layoutStorage = React.useMemo(
    () => (typeof window !== "undefined" ? window.localStorage : { getItem: () => null, setItem: () => {} }), []);
  const { defaultLayout, onLayoutChanged } = useDefaultLayout({ id: "cockpit-cols-video", storage: layoutStorage });

  return (
    <div className="col-span-2 flex min-h-0 flex-col overflow-hidden bg-surface">
      <PipelineRail step={c.videoStep} steps={VIDEO_STEPS} gate={c.videoGate} busy={busy}
        onAdvance={() => act("advance")} onRegenerate={() => act("regenerate")}
        settingsOpen={showSettings} onToggleSettings={() => setShowSettings((v) => !v)} />
      {showSettings && (
        <div className="border-b border-outline-variant bg-surface-container-low">
          <VideoSettings bypass={c.videoBypass} onToggle={c.setVideoBypass} />
        </div>
      )}
      <Group orientation="horizontal" defaultLayout={defaultLayout} onLayoutChanged={onLayoutChanged}
        className="min-h-0 flex-1 overflow-hidden">
        <Panel id="video-vfs" collapsible defaultSize={16} minSize={10} collapsedSize={3}
          className="min-h-0 overflow-hidden border-r border-outline-variant">
          <FileTree />
        </Panel>
        <Separator className="w-px bg-outline-variant data-[separator=hover]:bg-on-surface-variant data-[separator=active]:bg-on-surface-variant" />
        <Panel id="video-canvas" defaultSize={60} minSize={36} className="min-h-0 overflow-hidden">
          <div className="flex h-full flex-col items-center justify-center gap-2 px-8 text-center">
            <p className="text-body-lg font-medium text-on-surface">영상 에디터</p>
            <p className="max-w-sm text-body-sm text-on-surface-variant">
              콘티가 생성되면 여기서 라이브 프리뷰·타임라인으로 편집하고 확정해 렌더할 수 있습니다. 우측 챗으로 지시하거나 좌측 트리에서 storyboard.spec.json을 선택하세요.
            </p>
          </div>
        </Panel>
        <Separator className="w-px bg-outline-variant data-[separator=hover]:bg-on-surface-variant data-[separator=active]:bg-on-surface-variant" />
        <Panel id="video-chat" collapsible defaultSize={24} minSize={16} collapsedSize={3}
          className="min-h-0 overflow-hidden border-l border-outline-variant">
          <div className="flex min-h-0 flex-col">
            <div className="flex items-center gap-1.5 border-b border-outline-variant bg-surface-container-low px-3 py-2">
              <span className="mr-1 text-caption text-on-surface-variant">언어</span>
              {LANGS.map((l) => (
                <button key={l} type="button" onClick={() => void c.switchVideoLang(l)}
                  className={cn("rounded-full px-2.5 py-1 text-caption", c.videoLang === l ? "bg-primary text-on-primary" : "text-on-surface-variant hover:bg-surface-container-high")}>
                  {l}
                </button>
              ))}
            </div>
            <div className="min-h-0 flex-1 overflow-hidden"><ChatPane /></div>
          </div>
        </Panel>
      </Group>
    </div>
  );
}
