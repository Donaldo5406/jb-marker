"use client";

import * as React from "react";
import { useCockpit } from "./CockpitProvider";
import { EditorPane } from "./EditorPane";
import { ChatPane } from "./ChatPane";
import { PipelineRail } from "./PipelineRail";

const LANGS = ["ko", "vi", "en"];

/** design 탭 본문: 중앙=PipelineRail+EditorPane, 우측=언어 스위처+ChatPane. */
export function DesignStudio() {
  const c = useCockpit();
  const [busy, setBusy] = React.useState(false);
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
              onClick={() => c.setDesignLang(l)}
              className={
                "rounded-full px-2.5 py-1 text-caption " +
                (c.designLang === l ? "bg-primary text-on-primary" : "text-on-surface-variant")
              }
            >
              {l}
            </button>
          ))}
        </div>
        <div className="min-h-0 flex-1 overflow-hidden">
          <ChatPane />
        </div>
      </div>
    </>
  );
}
