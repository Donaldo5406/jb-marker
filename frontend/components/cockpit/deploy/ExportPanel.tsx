"use client";

import * as React from "react";
import { FileArchive, Loader2 } from "lucide-react";
import {
  collectExportItems,
  buildCampaignManifest,
  buildCampaignZip,
  triggerDownload,
} from "@/lib/deployExport";
import type { ReviewGate, VfsNode } from "@/lib/api";
import type { EligibilityResult } from "../CockpitProvider";

export type ExportPanelProps = {
  runId: string | null;
  nodes: VfsNode[];
  title: string | null;
  channels: string[];
  eligibility: EligibilityResult | null;
  gate: ReviewGate | null;
};

type Status = "idle" | "working" | "done" | "error";

const CATEGORY_LABEL: Record<string, string> = {
  visual: "비주얼",
  report: "검토 리포트",
  verdict: "판정",
  package: "발송 패키지",
};

/** 최종 산출물 export — 산출물 카테고리 요약 + 전체 ZIP 다운로드. */
export function ExportPanel({ runId, nodes, title, channels, eligibility, gate }: ExportPanelProps) {
  const [status, setStatus] = React.useState<Status>("idle");
  const items = React.useMemo(() => (runId ? collectExportItems(runId, nodes) : []), [runId, nodes]);
  const summary = React.useMemo(() => {
    const m = new Map<string, number>();
    for (const it of items) m.set(it.category, (m.get(it.category) ?? 0) + 1);
    return [...m.entries()];
  }, [items]);

  const onExport = async () => {
    if (!runId || items.length === 0) return;
    setStatus("working");
    try {
      const manifest = buildCampaignManifest({
        runId,
        title,
        generatedAt: new Date().toISOString(),
        channels,
        eligibility,
        reviewGate: gate,
        items,
      });
      const blob = await buildCampaignZip(runId, items, manifest);
      triggerDownload(blob, `marker-campaign-${runId}.zip`);
      setStatus("done");
    } catch {
      setStatus("error");
    }
  };

  return (
    <div className="space-y-3" data-testid="export-panel">
      {items.length === 0 ? (
        <p className="text-caption text-on-surface-variant">아직 export할 산출물이 없습니다. 파이프라인을 진행하세요.</p>
      ) : (
        <ul className="flex flex-wrap gap-2">
          {summary.map(([cat, n]) => (
            <li key={cat} className="rounded-lg bg-surface-container px-2.5 py-1 text-caption text-on-surface-variant">
              {CATEGORY_LABEL[cat] ?? cat} <b className="text-on-surface">{n}</b>
            </li>
          ))}
        </ul>
      )}
      <button
        type="button"
        data-testid="export-zip-btn"
        onClick={onExport}
        disabled={items.length === 0 || status === "working"}
        className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-body-sm font-medium text-on-primary hover:bg-primary-container disabled:bg-surface-container disabled:text-on-surface-variant"
      >
        {status === "working" ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
        ) : (
          <FileArchive className="h-4 w-4" aria-hidden />
        )}
        {status === "working" ? "묶는 중…" : "전체 ZIP 다운로드"}
        {items.length > 0 && <span className="opacity-80">({items.length})</span>}
      </button>
      {status === "done" && <p className="text-caption text-severity-ok-fg">ZIP 다운로드를 시작했습니다.</p>}
      {status === "error" && <p className="text-caption text-severity-critical-fg">export에 실패했습니다. 다시 시도하세요.</p>}
    </div>
  );
}
