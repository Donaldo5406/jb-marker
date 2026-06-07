"use client";

import * as React from "react";
import { useCockpit } from "./CockpitProvider";
import { StepProgress, type Step } from "./StepProgress";
import { ViolationCard } from "./review/ViolationCard";
import { EquivalenceCard } from "./review/EquivalenceCard";
import { ReconcilerSummary } from "./review/ReconcilerSummary";
import { VerdictPanel } from "./review/VerdictPanel";
import { loadReviewVerdicts, loadReviewReport, type ReviewVerdict } from "@/lib/reviewArtifacts";

const STEPS: Step[] = [
  { id: "R0", label: "셋업" },
  { id: "R1", label: "법률" },
  { id: "R2", label: "동등성" },
  { id: "R3", label: "통합" },
  { id: "done", label: "완료" },
];

export function ReviewStudio() {
  const c = useCockpit();
  const stage = c.reviewStage ?? "R0";
  const status = c.manifest?.step_status?.review;
  const [busy, setBusy] = React.useState(false);
  const [verdicts, setVerdicts] = React.useState<ReviewVerdict[]>([]);
  const [report, setReport] = React.useState<string | null>(null);

  // 트리/run 변화 시 산출물 로드(읽기 전용).
  React.useEffect(() => {
    if (!c.runId) return;
    let cancelled = false;
    void (async () => {
      const [vs, rep] = await Promise.all([loadReviewVerdicts(c.runId!, c.nodes), loadReviewReport(c.runId!)]);
      if (!cancelled) {
        setVerdicts(vs);
        setReport(rep);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [c.runId, c.nodes]);

  const run = async () => {
    setBusy(true);
    try {
      await c.runReview();
    } finally {
      setBusy(false);
    }
  };
  const legal = verdicts.filter((v) => v.node === "legal");
  const i18n = verdicts.filter((v) => v.node === "i18n");
  const empty = verdicts.length === 0 && !report;

  return (
    <div className="col-span-2 flex min-h-0 flex-col overflow-hidden bg-surface">
      <div className="border-b border-outline-variant bg-surface-container-low px-6 py-3">
        <StepProgress steps={STEPS} currentId={stage} />
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-[1.7fr_1fr] gap-4 overflow-auto p-6">
        {/* 좌: 근거 본문 */}
        <div className="space-y-4">
          {empty ? (
            <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-outline-variant py-16 text-center">
              <p className="text-body-sm font-medium text-on-surface">아직 검토 결과가 없습니다</p>
              <p className="max-w-xs text-caption text-on-surface-variant">우측 패널에서 검토를 시작하면 법률·동등성 근거가 여기에 표시됩니다.</p>
            </div>
          ) : (
            <>
              {legal.length > 0 && (
                <section className="space-y-2" aria-label="법률 검토">
                  <h3 className="text-caption uppercase tracking-wide text-on-surface-variant">법률 검토 (R1)</h3>
                  {legal.map((v, i) => <ViolationCard key={v.verdict_id ?? i} v={v} />)}
                </section>
              )}
              {i18n.length > 0 && (
                <section className="space-y-2" aria-label="동등성 검토">
                  <h3 className="text-caption uppercase tracking-wide text-on-surface-variant">동등성 검토 (R2)</h3>
                  {i18n.map((v, i) => <EquivalenceCard key={v.verdict_id ?? i} v={v} />)}
                </section>
              )}
              <ReconcilerSummary report={report} />
            </>
          )}
        </div>

        {/* 우: 심의 판정 */}
        <div>
          <VerdictPanel
            status={status}
            gate={c.reviewGate ? { critical: c.reviewGate.critical, warning: c.reviewGate.warning } : null}
            acknowledged={c.reviewAcknowledged}
            stage={stage}
            busy={busy}
            onRun={run}
            onAck={() => void c.ackReview()}
            onRestart={() => void c.restartReview()}
            onBackToDesign={() => c.setStudio("design")}
          />
        </div>
      </div>
    </div>
  );
}
