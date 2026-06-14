"use client";

import * as React from "react";
import { Loader2, CheckCircle2 } from "lucide-react";
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

// 검토 진행 중 단계별 "AI 검토중" 안내 문구.
const PROGRESS_MSG: Record<string, string> = {
  R0: "검토 환경을 준비하고 있습니다…",
  R1: "AI가 표시광고법·금융소비자보호법 위반을 검토 중입니다…",
  R2: "다국어 자산의 필수고지 동등성을 검토 중입니다…",
  R3: "검토 결과를 통합하고 우선순위를 매기는 중입니다…",
  done: "검토 결과를 정리하고 있습니다…",
};

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
  // 재검토: signal 초기화(R0) 후 곧바로 전체 재검토를 구동 — 한 클릭에 완주 + 로딩 표시
  // (이전: restart만 호출해 R0로만 되돌아가 '반응 없음'처럼 보임).
  const restart = async () => {
    setBusy(true);
    try { await c.restartReview(); await c.runReview(); } finally { setBusy(false); }
  };
  // 경고 확인 후 Deploy 진입 — ack 처리 동안 로딩, 완료 시 deploy로 전환.
  const ack = async () => {
    setBusy(true);
    try { await c.ackReview(); c.setStudio("deploy"); } finally { setBusy(false); }
  };
  const legal = verdicts.filter((v) => v.node === "legal");
  const i18n = verdicts.filter((v) => v.node === "i18n");
  const empty = verdicts.length === 0 && !report;
  // 위반·경고 0으로 종료 = 깔끔한 통과. 보고서 빈 섹션 대신 '없음' 카드를 보여준다.
  const clean = stage === "done" && !!c.reviewGate && c.reviewGate.critical === 0 && c.reviewGate.warning === 0;

  return (
    <div className="col-span-2 flex min-h-0 flex-col overflow-hidden bg-surface">
      <div className="border-b border-outline-variant bg-surface-container-low px-6 py-3">
        <StepProgress steps={STEPS} currentId={stage} />
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-[1.7fr_1fr] gap-4 overflow-auto p-6">
        {/* 좌: 근거 본문 */}
        <div className="space-y-4">
          {busy && (
            <div
              className="flex items-center gap-3 rounded-lg border border-primary/30 bg-primary/5 px-4 py-3"
              role="status"
              aria-live="polite"
            >
              <Loader2 className="h-4 w-4 shrink-0 animate-spin text-primary" aria-hidden />
              <div className="min-w-0">
                <p className="text-body-sm font-medium text-on-surface">AI가 검토 중입니다</p>
                <p className="truncate text-caption text-on-surface-variant">
                  {PROGRESS_MSG[stage] ?? "검토를 진행하고 있습니다…"}
                </p>
              </div>
            </div>
          )}
          {empty && !busy ? (
            <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-outline-variant py-16 text-center">
              <p className="text-body-sm font-medium text-on-surface">아직 검토 결과가 없습니다</p>
              <p className="max-w-xs text-caption text-on-surface-variant">우측 패널에서 검토를 시작하면 법률·동등성 근거가 여기에 표시됩니다.</p>
            </div>
          ) : empty && busy ? null : clean && !busy ? (
            <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-severity-ok bg-severity-ok-bg py-16 text-center" data-testid="review-clean">
              <CheckCircle2 className="h-6 w-6 text-severity-ok-fg" aria-hidden />
              <p className="text-body-sm font-medium text-severity-ok-fg">검토 완료 — 위반·권장 사항이 없습니다</p>
              <p className="max-w-xs text-caption text-severity-ok-fg">모든 법률·동등성 항목을 통과했습니다. Deploy로 진행할 수 있습니다.</p>
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
            actions={c.reviewGate?.actions ?? []}
            acknowledged={c.reviewAcknowledged}
            stage={stage}
            busy={busy}
            onRun={run}
            onAck={ack}
            onRestart={restart}
            onBackToDesign={() => c.setStudio("design")}
            onProceedDeploy={() => c.setStudio("deploy")}
          />
        </div>
      </div>
    </div>
  );
}
