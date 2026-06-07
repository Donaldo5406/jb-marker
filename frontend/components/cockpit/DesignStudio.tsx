"use client";

import * as React from "react";
import { X } from "lucide-react";
import { useCockpit } from "./CockpitProvider";
import { FileContent } from "./FileContent";
import { ChatPane } from "./ChatPane";
import { PipelineRail } from "./PipelineRail";
import { DesignSettings } from "./DesignSettings";
import { displayName, baseName } from "@/lib/fileType";
import { cn } from "@/lib/utils";

const LANGS = ["ko", "vi", "en"];

/** design 탭: col-span-2 단일 컨테이너.
 *  상단=PipelineRail(StepProgress+액션+⚙) / [⚙시 스킵 스코프 드롭다운] /
 *  하단=중앙 씬 에디터(상시) + 우측 AI 챗(상시, 언어 스위처 포함). */
export function DesignStudio() {
  const c = useCockpit();
  const [busy, setBusy] = React.useState(false);
  const [showSettings, setShowSettings] = React.useState(false);
  const act = async (action: string) => {
    setBusy(true);
    try {
      await c.runDesign(action);
    } finally {
      setBusy(false);
    }
  };
  const sceneOpen = !!c.openFile && c.openFile.path.endsWith(".scene");

  return (
    <div className="col-span-2 flex min-h-0 flex-col overflow-hidden bg-surface">
      <PipelineRail
        step={c.designStep}
        gate={c.designGate}
        busy={busy}
        onAdvance={() => act("advance")}
        onRegenerate={() => act("regenerate")}
        settingsOpen={showSettings}
        onToggleSettings={() => setShowSettings((v) => !v)}
      />
      {showSettings && (
        <div className="border-b border-outline-variant bg-surface-container-low">
          <DesignSettings bypass={c.designBypass} onToggle={c.setDesignBypass} />
        </div>
      )}

      <div className="flex min-h-0 flex-1">
        {/* 중앙: 활성 씬 에디터(수동 편집) 상시, 없으면 안내 */}
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden border-r border-outline-variant">
          {sceneOpen && c.openFile ? (
            <>
              <div className="flex items-center gap-2 border-b border-outline-variant bg-surface-container-low px-3 py-2">
                <span className="flex-1 truncate text-body-sm font-medium text-on-surface">{displayName(baseName(c.openFile.path))}</span>
                <button type="button" onClick={c.closeFile} aria-label="씬 닫기" title="닫기"
                  className="inline-flex h-7 w-7 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container-high">
                  <X className="h-4 w-4" aria-hidden />
                </button>
              </div>
              <FileContent file={c.openFile} runId={c.runId} onChangeContent={c.setOpenFileContent} onSaveScene={c.saveSceneJson} />
            </>
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-2 px-8 text-center">
              <p className="text-body-lg font-medium text-on-surface">디자인 캔버스</p>
              <p className="max-w-sm text-body-sm text-on-surface-variant">
                Final 단계에서 씬이 생성되면 여기서 직접 편집할 수 있습니다. 우측 챗으로 지시하거나 좌측 트리에서 main.scene을 선택하세요.
              </p>
            </div>
          )}
        </div>

        {/* 우측: 언어 스위처 + AI 챗(상시) */}
        <div className="flex min-h-0 w-[360px] flex-col overflow-hidden">
          <div className="flex items-center gap-1.5 border-b border-outline-variant bg-surface-container-low px-3 py-2">
            <span className="mr-1 text-caption text-on-surface-variant">언어</span>
            {LANGS.map((l) => (
              <button key={l} type="button" onClick={() => void c.switchDesignLang(l)}
                className={cn("rounded-full px-2.5 py-1 text-caption", c.designLang === l ? "bg-primary text-on-primary" : "text-on-surface-variant hover:bg-surface-container-high")}>
                {l}
              </button>
            ))}
          </div>
          <div className="min-h-0 flex-1 overflow-hidden">
            <ChatPane />
          </div>
        </div>
      </div>
    </div>
  );
}
