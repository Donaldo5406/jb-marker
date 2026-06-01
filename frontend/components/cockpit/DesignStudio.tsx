"use client";

import * as React from "react";
import { Settings } from "lucide-react";
import { useCockpit } from "./CockpitProvider";
import { EditorPane } from "./EditorPane";
import { ChatPane } from "./ChatPane";
import { PipelineRail } from "./PipelineRail";
import { DesignSettings } from "./DesignSettings";

const LANGS = ["ko", "vi", "en"];

/** design 탭 본문: 중앙=PipelineRail+EditorPane, 우측=언어 스위처+ChatPane. */
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
  return (
    <>
      <div className="flex min-h-0 flex-col overflow-hidden border-r border-outline-variant">
        <PipelineRail
          step={c.designStep}
          gate={c.designGate}
          busy={busy}
          onAdvance={() => act("advance")}
          onRegenerate={() => act("regenerate")}
        />
        <div className="min-h-0 flex-1 overflow-hidden">
          <EditorPane />
        </div>
      </div>
      <div className="flex min-h-0 flex-col overflow-hidden">
        <div className="flex items-center gap-1.5 border-b border-outline-variant bg-surface-container-low px-3 py-2">
          {LANGS.map((l) => (
            <button
              key={l}
              type="button"
              onClick={() => void c.switchDesignLang(l)}
              className={
                "rounded-full px-2.5 py-1 text-caption " +
                (c.designLang === l ? "bg-primary text-on-primary" : "text-on-surface-variant")
              }
            >
              {l}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setShowSettings((v) => !v)}
            aria-label="디자인 설정"
            aria-pressed={showSettings}
            title="자동 진행(confirm 게이트) 설정"
            className={
              "ml-auto inline-flex h-7 w-7 items-center justify-center rounded-full transition-colors " +
              (showSettings ? "bg-primary text-on-primary" : "text-on-surface-variant hover:bg-surface-container-high")
            }
          >
            <Settings className="h-4 w-4" aria-hidden />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-hidden">
          {showSettings ? (
            <DesignSettings bypass={c.designBypass} onToggle={c.setDesignBypass} />
          ) : (
            <ChatPane />
          )}
        </div>
      </div>
    </>
  );
}
