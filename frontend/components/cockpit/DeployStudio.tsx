"use client";

import * as React from "react";
import { Lock, X } from "lucide-react";
import Link from "next/link";
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
import { DemoPaymentModal } from "@/components/cockpit/deploy/DemoPaymentModal";
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

export function DeployStudio() {
  const c = useCockpit();
  const selected = c.selectedProviders;
  const setSelected = c.setSelectedProviders;
  const [activeAdvisor, setActiveAdvisor] = React.useState<{ channel: string; lang: string } | null>(null);
  const [paymentOpen, setPaymentOpen] = React.useState(false);
  const [calendar, setCalendar] = React.useState<{ hour: number; blocked: boolean }[]>([]);
  const [verdicts, setVerdicts] = React.useState<ReviewVerdict[]>([]);

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

  const languages: string[] = ["ko"];
  const matrix = selected.flatMap((ch) => languages.map((l) => ({ channel: ch, lang: l })));
  const currentStep = !c.eligibility ? "D0" : Object.keys(c.packages).length === 0 ? "D1" : "D2";
  const designDone = c.manifest?.step_status?.design === "done" || c.designStep === "done";

  // ₩150,000 (Pro+) 게이트 — deploy 엔타이틀먼트 없으면 잠금 안내.
  if (!c.entitlement.deploy) {
    return (
      <div className="col-span-2 flex min-h-0 flex-col items-center justify-center gap-4 bg-surface px-6 text-center" data-testid="deploy-locked">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-container text-on-surface-variant">
          <Lock className="h-5 w-5" aria-hidden />
        </div>
        <div className="space-y-1">
          <h2 className="text-h3 text-on-surface">Deploy 스튜디오는 Pro+ 전용</h2>
          <p className="max-w-sm text-body-sm text-on-surface-variant">채널 발송·§50 적법성·발송 어드바이저는 ₩150,000 Pro+ 플랜에서 제공됩니다.</p>
        </div>
        <Link href="/pricing" className="rounded-full bg-primary px-4 py-2 text-body-sm font-medium text-on-primary hover:bg-primary-container">
          요금제 보기
        </Link>
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
          <div className="space-y-3">
            <ProviderGrid providers={SEED_PROVIDERS} selected={selected} onChange={setSelected} />
            <button
              type="button"
              onClick={async () => {
                await c.setupDeploy(selected, languages);
                await c.runEligibility();
                setCalendar(Array.from({ length: 24 }, (_, h) => ({ hour: h, blocked: h >= 21 || h < 8 })));
              }}
              disabled={selected.length === 0}
              className="rounded-lg bg-primary px-3 py-2 text-body-sm font-medium text-on-primary hover:bg-primary-container disabled:bg-surface-container disabled:text-on-surface-variant"
            >
              적법성 검사 실행
            </button>
          </div>
        </DeployCard>

        {c.eligibility && (
          <DeployCard step="D1" title="발송 적법성 (정보통신망법 §50)" desc="수신자별 동의·야간(21~08)·옵트아웃을 판정해 발송대상/제외를 가립니다.">
            <EligibilityPanel total={c.eligibility.total} eligibleCount={c.eligibility.eligible_count} excludedCount={c.eligibility.excluded_count} calendar={calendar} />
          </DeployCard>
        )}

        {c.eligibility && matrix.length > 0 && (
          <DeployCard step="D2" title="채널 패키징" desc="선택 채널×언어별로 규격에 맞춰 export 패키지를 생성합니다.">
            <div className="space-y-3">
              <button
                type="button"
                onClick={async () => {
                  for (const cell of matrix) {
                    await c.runPackagingCell(cell.channel, cell.lang, "demo copy " + cell.channel, `/runs/${c.runId}/deploy/packages/${cell.channel}_${cell.lang}/visual.png`);
                  }
                }}
                className="rounded-lg bg-primary px-3 py-2 text-body-sm font-medium text-on-primary hover:bg-primary-container"
              >
                전체 패키징 실행
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
              devPass={c.devPass}
              onConfirm={async () => {
                const res = await c.dispatchConfirm();
                if (res.needsPayment) setPaymentOpen(true);
              }}
              onPayDemo={() => setPaymentOpen(true)}
            />
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
                onPayDemo={() => setPaymentOpen(true)}
              />
            </div>
          </div>
        </div>
      )}

      <DemoPaymentModal open={paymentOpen} onClose={() => setPaymentOpen(false)} onPayDemo={() => void c.payDemo()} />
    </div>
  );
}
