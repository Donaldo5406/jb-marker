"use client";
import * as React from "react";
import { Group, Panel, Separator, useDefaultLayout } from "react-resizable-panels";
import { useCockpit } from "./CockpitProvider";
import { FileTree } from "./FileTree";
import { FileContent } from "./FileContent";
import { ChatPane } from "./ChatPane";
import { PipelineRail } from "./PipelineRail";
import { DesignSettings } from "./DesignSettings";
import { ConfirmToastView } from "./ConfirmToast";
import { cn } from "@/lib/utils";

const LANGS = ["ko", "en", "vi", "zh"];

/** design 탭: 상단 PipelineRail + 하단 4-panel(VFS·캔버스·미사용 안내·챗).
 *  VFS·챗 Panel은 collapsible. 캔버스 영역은 DesignEditor(자체 인스펙터/툴바)를 렌더. */
export function DesignStudio() {
  const c = useCockpit();
  const [busy, setBusy] = React.useState(false);
  const [showSettings, setShowSettings] = React.useState(false);
  const act = async (action: string) => { setBusy(true); try { await c.runDesign(action); } finally { setBusy(false); } };
  const sceneOpen = !!c.openFile && c.openFile.path.endsWith(".scene");
  const layoutStorage = React.useMemo(
    () => (typeof window !== "undefined" ? window.localStorage : { getItem: () => null, setItem: () => {} }), []);
  const { defaultLayout, onLayoutChanged } = useDefaultLayout({ id: "cockpit-cols-design", storage: layoutStorage });

  return (
    <div className="col-span-2 flex min-h-0 flex-col overflow-hidden bg-surface">
      <PipelineRail step={c.designStep} gate={c.designGate} busy={busy}
        onAdvance={() => act("advance")} onRegenerate={() => act("regenerate")}
        settingsOpen={showSettings} onToggleSettings={() => setShowSettings((v) => !v)} />
      {showSettings && (
        <div className="border-b border-outline-variant bg-surface-container-low">
          <DesignSettings bypass={c.designBypass} onToggle={c.setDesignBypass} />
        </div>
      )}
      <Group orientation="horizontal" defaultLayout={defaultLayout} onLayoutChanged={onLayoutChanged}
        className="min-h-0 flex-1 overflow-hidden">
        <Panel id="design-vfs" collapsible defaultSize={16} minSize={10} collapsedSize={3}
          className="min-h-0 overflow-hidden border-r border-outline-variant">
          <FileTree />
        </Panel>
        <Separator className="w-px bg-outline-variant data-[separator=hover]:bg-on-surface-variant data-[separator=active]:bg-on-surface-variant" />
        <Panel id="design-canvas" defaultSize={60} minSize={36} className="min-h-0 overflow-hidden">
          {sceneOpen && c.openFile ? (
            <FileContent file={c.openFile} runId={c.runId} onChangeContent={c.setOpenFileContent} onSaveScene={c.saveSceneJson} />
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-2 px-8 text-center">
              <p className="text-body-lg font-medium text-on-surface">디자인 캔버스</p>
              <p className="max-w-sm text-body-sm text-on-surface-variant">
                Final 단계에서 씬이 생성되면 여기서 직접 편집할 수 있습니다. 우측 챗으로 지시하거나 좌측 트리에서 main.scene을 선택하세요.
              </p>
            </div>
          )}
        </Panel>
        <Separator className="w-px bg-outline-variant data-[separator=hover]:bg-on-surface-variant data-[separator=active]:bg-on-surface-variant" />
        <Panel id="design-chat" collapsible defaultSize={24} minSize={16} collapsedSize={3}
          className="min-h-0 overflow-hidden border-l border-outline-variant">
          <div className="flex h-full min-h-0 flex-col">
            <div className="flex items-center gap-1.5 border-b border-outline-variant bg-surface-container-low px-3 py-2">
              <span className="mr-1 text-caption text-on-surface-variant">언어</span>
              {LANGS.map((l) => (
                <button key={l} type="button" onClick={() => void c.switchDesignLang(l)}
                  className={cn("rounded-full px-2.5 py-1 text-caption", c.designLang === l ? "bg-primary text-on-primary" : "text-on-surface-variant hover:bg-surface-container-high")}>
                  {l}
                </button>
              ))}
            </div>
            <div className="min-h-0 flex-1 overflow-hidden"><ChatPane /></div>
          </div>
        </Panel>
      </Group>
      <ConfirmToastView open={c.regenConfirm.open}
        message="수동 편집한 씬이 있습니다. 재생성하면 편집 내용이 새 씬으로 대체됩니다. 계속할까요?"
        confirmLabel="재생성" cancelLabel="취소"
        onConfirm={c.regenConfirm.onConfirm} onCancel={c.regenConfirm.onCancel} />
    </div>
  );
}
