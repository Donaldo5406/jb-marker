"use client";

import * as React from "react";
import { Lock, X, CheckCircle2, AlertTriangle, FileText, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { useCockpit } from "@/components/cockpit/CockpitProvider";
import { StepProgress, type Step } from "@/components/cockpit/StepProgress";
import { DeployCard } from "@/components/cockpit/deploy/DeployCard";
import { PreDeployReview } from "@/components/cockpit/deploy/PreDeployReview";
import { ExportPanel } from "@/components/cockpit/deploy/ExportPanel";
import { ProviderGrid, type ProviderEntry } from "@/components/cockpit/deploy/ProviderGrid";
import { EligibilityPanel } from "@/components/cockpit/deploy/EligibilityPanel";
import { PackageMatrix } from "@/components/cockpit/deploy/PackageMatrix";
import { AdvisorChat } from "@/components/cockpit/deploy/AdvisorChat";
import { DispatchConfirm } from "@/components/cockpit/deploy/DispatchConfirm";
import { RecipientImport, type Recipient } from "@/components/cockpit/deploy/RecipientImport";
import { loadReviewVerdicts, type ReviewVerdict } from "@/lib/reviewArtifacts";

const SEED_PROVIDERS: ProviderEntry[] = [
  { id: "email", name: "이메일", logo_path: "/providers/email.svg", channel_type: "email", adapter_status: "stub", priority: 1 },
  { id: "kakao", name: "카카오 알림톡", logo_path: "/providers/kakao.svg", channel_type: "messenger", adapter_status: "stub", priority: 2 },
  { id: "sms", name: "SMS", logo_path: "/providers/sms.svg", channel_type: "sms", adapter_status: "stub", priority: 3 },
  { id: "naver", name: "네이버 광고", logo_path: "/providers/naver.svg", channel_type: "ad", adapter_status: "stub", priority: 4 },
  { id: "google", name: "구글 광고", logo_path: "/providers/google.svg", channel_type: "ad", adapter_status: "stub", priority: 5 },
  { id: "instagram", name: "인스타그램", logo_path: "/providers/instagram.svg", channel_type: "social", adapter_status: "stub", priority: 6 },
];

const STEPS: Step[] = [
  { id: "D0", label: "채널" },
  { id: "D1", label: "적법성" },
  { id: "D2", label: "패키징" },
  { id: "D3", label: "발송" },
];

type DispatchCell = { channel: string; lang: string; status: string; message?: string; reason?: string; recipients_count?: number };
type DispatchSim = { step_status?: string; simulation?: DispatchCell[] };

export function DeployStudio() {
  const c = useCockpit();
  const selected = c.selectedProviders;
  const setSelected = c.setSelectedProviders;
  const [activeAdvisor, setActiveAdvisor] = React.useState<{ channel: string; lang: string } | null>(null);
  const [calendar, setCalendar] = React.useState<{ hour: number; blocked: boolean }[]>([]);
  const [verdicts, setVerdicts] = React.useState<ReviewVerdict[]>([]);
  const [dispatch, setDispatch] = React.useState<DispatchSim | null>(null);
  const [dispatching, setDispatching] = React.useState(false);
  const [dispatchError, setDispatchError] = React.useState<string | null>(null);
  // 업로드 발송 명단(없으면 백엔드 내장 동의대장 사용) + 버튼 로딩 상태.
  const [importedRecipients, setImportedRecipients] = React.useState<Recipient[] | null>(null);
  const [eligLoading, setEligLoading] = React.useState(false);
  const [pkgProgress, setPkgProgress] = React.useState<{ done: number; total: number } | null>(null);
  // T9: Design 산출(layout.spec.json)의 실제 4언어 카피를 패키징 입력으로 사용(더미 제거).
  const [languages, setLanguages] = React.useState<string[]>(["ko"]);
  const [designCopy, setDesignCopy] = React.useState<Record<string, Record<string, string>>>({});

  React.useEffect(() => {
    if (!activeAdvisor) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setActiveAdvisor(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [activeAdvisor]);

  // 검토 verdict 노드 경로 집합을 안정 키로 — 폴링(c.nodes 식별자 변동)마다 재페치하지 않도록.
  const verdictKey = React.useMemo(
    () => c.nodes.filter((n) => /\/review\/(legal|i18n)\/[^/]+\/verdict\.json$/.test(n.path)).map((n) => n.path).join("|"),
    [c.nodes],
  );
  React.useEffect(() => {
    if (!c.runId) return;
    let cancelled = false;
    void loadReviewVerdicts(c.runId, c.nodes).then((v) => {
      if (!cancelled) setVerdicts(v);
    });
    return () => {
      cancelled = true;
    };
    // c.nodes는 verdictKey에 반영됨 — verdict 노드 변동 시에만 재로드.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [c.runId, verdictKey]);

  // T9: Design 산출 layout.spec.json에서 실제 언어셋·카피 로드(없으면 ko 기본 유지).
  React.useEffect(() => {
    if (!c.runId) return;
    let cancelled = false;
    void (async () => {
      try {
        const node = await api.vfsGet(c.runId!, "design/rough/layout.spec.json");
        const spec = JSON.parse(node.content_text ?? "{}");
        const copy = (spec.copy ?? {}) as Record<string, Record<string, string>>;
        const langs = Object.keys(copy);
        if (!cancelled && langs.length > 0) {
          setDesignCopy(copy);
          setLanguages(langs);
        }
      } catch {
        /* design 미완 — ko 기본 유지 */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [c.runId]);

  const matrix = selected.flatMap((ch) => languages.map((l) => ({ channel: ch, lang: l })));
  const currentStep = !c.eligibility ? "D0" : Object.keys(c.packages).length === 0 ? "D1" : "D2";
  const designDone = c.manifest?.step_status?.design === "done" || c.designStep === "done";

  // Pro+ 엔타이틀먼트 게이트 — 없으면 잠금 안내(결제 표면 폐기 2026-07-04, Setting 토글로 해제).
  if (!c.entitlement.deploy) {
    return (
      <div className="col-span-2 flex min-h-0 flex-col items-center justify-center gap-4 bg-surface px-6 text-center" data-testid="deploy-locked">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-container text-on-surface-variant">
          <Lock className="h-5 w-5" aria-hidden />
        </div>
        <div className="space-y-1">
          <h2 className="text-h3 text-on-surface">Deploy 스튜디오는 Pro+ 전용</h2>
          <p className="max-w-sm text-body-sm text-on-surface-variant">채널 발송·§50 적법성·발송 어드바이저는 Pro+ 엔타이틀먼트에서 제공됩니다.</p>
        </div>
        <p className="text-caption text-on-surface-variant">데모: 콕핏 Setting에서 Deploy 엔타이틀먼트를 켜면 체험할 수 있습니다.</p>
      </div>
    );
  }

  return (
    <div className="col-span-2 flex min-h-0 flex-col overflow-hidden bg-surface" data-testid="deploy-studio">
      <div className="border-b border-outline-variant bg-surface-container-low px-6 py-3">
        <StepProgress steps={STEPS} currentId={currentStep} />
      </div>

      <div className="min-h-0 flex-1 space-y-4 overflow-auto p-6">
        <DeployCard title="배포 전 검토 요약" desc="이 캠페인이 발송 전에 통과한 검토 결과입니다.">
          <PreDeployReview designDone={designDone} gate={c.reviewGate} verdicts={verdicts} />
        </DeployCard>

        <DeployCard step="D0" title="발송 채널 선택" desc="발송할 채널을 고르세요. 각 어댑터 상태(stub/live)를 함께 표시합니다.">
          <div className="space-y-4">
            <ProviderGrid providers={SEED_PROVIDERS} selected={selected} onChange={setSelected} />
            <div className="space-y-2">
              <p className="text-caption font-medium text-on-surface-variant">
                발송 명단 (선택) — 미업로드 시 내장 동의대장 샘플로 검사합니다.
              </p>
              <RecipientImport
                onApply={(r) => setImportedRecipients(r)}
                appliedCount={importedRecipients?.length ?? null}
              />
            </div>
            <button
              type="button"
              onClick={async () => {
                setEligLoading(true);
                try {
                  await c.setupDeploy(selected, languages);
                  await c.runEligibility(importedRecipients ?? undefined);
                  setCalendar(Array.from({ length: 24 }, (_, h) => ({ hour: h, blocked: h >= 21 || h < 8 })));
                } finally {
                  setEligLoading(false);
                }
              }}
              disabled={selected.length === 0 || eligLoading}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-body-sm font-medium text-on-primary hover:bg-primary-container disabled:bg-surface-container disabled:text-on-surface-variant"
            >
              {eligLoading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
              {eligLoading ? "적법성 검사 중…" : "적법성 검사 실행"}
            </button>
          </div>
        </DeployCard>

        {c.eligibility && (
          <DeployCard step="D1" title="발송 적법성 (정보통신망법 §50 · 개인정보보호법 §15·§16)" desc="수신자별 동의·야간(21~08)·옵트아웃(§50)과 수집목적·보유기간(§15·§16)을 판정해 발송대상/제외를 가립니다.">
            <EligibilityPanel total={c.eligibility.total} eligibleCount={c.eligibility.eligible_count} excludedCount={c.eligibility.excluded_count} calendar={calendar} breakdown={c.eligibility.breakdown} />
          </DeployCard>
        )}

        {c.eligibility && matrix.length > 0 && (
          <DeployCard step="D2" title="채널 패키징" desc="선택 채널×언어별로 규격에 맞춰 export 패키지를 생성합니다.">
            <div className="space-y-3">
              <button
                type="button"
                onClick={async () => {
                  setPkgProgress({ done: 0, total: matrix.length });
                  try {
                    let done = 0;
                    for (const cell of matrix) {
                      const cp = designCopy[cell.lang] ?? {};
                      const copyText = [cp.headline, cp.body, cp.cta].filter(Boolean).join(" ").trim() || `demo copy ${cell.channel}`;
                      await c.runPackagingCell(cell.channel, cell.lang, copyText, `/runs/${c.runId}/deploy/packages/${cell.channel}_${cell.lang}/visual.png`);
                      done += 1;
                      setPkgProgress({ done, total: matrix.length });
                    }
                  } finally {
                    setPkgProgress(null);
                  }
                }}
                disabled={pkgProgress !== null}
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-body-sm font-medium text-on-primary hover:bg-primary-container disabled:bg-surface-container disabled:text-on-surface-variant"
              >
                {pkgProgress !== null && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
                {pkgProgress !== null ? `패키징 중… (${pkgProgress.done}/${pkgProgress.total})` : "전체 패키징 실행"}
              </button>
              <PackageMatrix
                cells={matrix.map((m) => ({ ...m, ...(c.packages[`${m.channel}_${m.lang}`] ?? {}) }))}
                onAskAdvisor={(channel, lang) => setActiveAdvisor({ channel, lang })}
              />
            </div>
          </DeployCard>
        )}

        <DeployCard title="최종 산출물 export" desc="캠페인 산출물(비주얼·카피·검토 리포트)을 ZIP 1개로 내려받습니다.">
          <ExportPanel
            runId={c.runId}
            nodes={c.nodes}
            title={c.manifest?.title ?? null}
            channels={selected}
            eligibility={c.eligibility}
            gate={c.reviewGate}
          />
        </DeployCard>

        {c.eligibility && (
          <DeployCard step="D3" title="발송 확정" desc="규칙엔진은 자동 발송하지 않습니다 — 최종 발송은 사용자 확정 게이트입니다.">
            <DispatchConfirm
              eligibleCount={c.eligibility.eligible_count}
              selectedCount={selected.length}
              busy={dispatching}
              onConfirm={async () => {
                setDispatching(true);
                setDispatchError(null);
                try {
                  const res = await c.dispatchConfirm();
                  if (res.error) {
                    setDispatchError(String(res.error));
                    return;
                  }
                  setDispatch(res as DispatchSim);
                } finally {
                  setDispatching(false);
                }
              }}
            />

            {dispatchError && (
              <p className="mt-2 text-caption text-error" role="alert">{dispatchError}</p>
            )}

            {dispatching && (
              <p className="mt-2 text-caption text-on-surface-variant" role="status" aria-live="polite">
                발송을 처리하고 있습니다…
              </p>
            )}

            {dispatch?.simulation && (
              <div className="mt-3 space-y-2 rounded-xl border border-outline-variant bg-surface-container-low p-4 animate-fade-in-up" data-testid="dispatch-result">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-primary" aria-hidden />
                    <p className="text-body-sm font-semibold text-on-surface">발송 완료 (시뮬레이션)</p>
                  </div>
                  {c.runId && (
                    <button
                      type="button"
                      onClick={() => void c.selectFile(`/${c.runId}/deploy/report.md`)}
                      className="inline-flex items-center gap-1.5 rounded-full border border-outline-variant px-3 py-1 text-caption font-medium text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface"
                    >
                      <FileText className="h-3.5 w-3.5" aria-hidden />
                      Deploy Report 보기
                    </button>
                  )}
                </div>
                <ul className="space-y-1.5">
                  {dispatch.simulation.map((s, i) => (
                    <li key={`${s.channel}_${s.lang}_${i}`} className="flex items-center justify-between gap-3 rounded-lg bg-surface px-3 py-2">
                      <span className="text-caption font-medium text-on-surface">{s.channel} · {s.lang}</span>
                      {s.status === "skipped" ? (
                        <span className="inline-flex items-center gap-1.5 text-caption text-error">
                          <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
                          건너뜀{s.reason ? ` — ${s.reason}` : ""}
                        </span>
                      ) : (
                        <span className="text-caption text-on-surface-variant">
                          [STUB] {s.recipients_count ?? 0}명 발송 · 시뮬레이션(실 연동 시 실제 발송)
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
                {dispatch.simulation.length === 0 && (
                  <p className="text-caption text-on-surface-variant">발송 대상 패키지가 없습니다. 패키징을 먼저 실행하세요.</p>
                )}
              </div>
            )}
          </DeployCard>
        )}
      </div>

      {activeAdvisor && (
        <div className="fixed inset-0 z-40" data-testid="advisor-drawer">
          <div className="absolute inset-0 bg-black/30" onClick={() => setActiveAdvisor(null)} aria-hidden />
          <div role="dialog" aria-label="발송 어드바이저" className="absolute right-0 top-0 flex h-full w-[min(440px,90vw)] flex-col bg-surface shadow-ambient animate-fade-in-up">
            <div className="flex items-center justify-between border-b border-outline-variant bg-surface-container-low px-4 py-2.5">
              <span className="text-body-sm font-medium text-on-surface">발송 어드바이저 · {activeAdvisor.channel}/{activeAdvisor.lang}</span>
              <button type="button" onClick={() => setActiveAdvisor(null)} aria-label="닫기" className="inline-flex h-7 w-7 items-center justify-center rounded-full text-on-surface-variant hover:bg-surface-container-high">
                <X className="h-4 w-4" aria-hidden />
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-auto p-3">
              <AdvisorChat
                packageId={`${activeAdvisor.channel}_${activeAdvisor.lang}`}
                onSubmit={(msg) => c.askAdvisor(`${activeAdvisor.channel}_${activeAdvisor.lang}`, msg)}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
