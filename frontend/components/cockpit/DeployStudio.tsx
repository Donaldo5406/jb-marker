"use client";

import * as React from "react";
import { Lock, X, CheckCircle2, AlertTriangle, FileText } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useCockpit } from "@/components/cockpit/CockpitProvider";
import { StepProgress, type Step } from "@/components/cockpit/StepProgress";
import { ProviderGrid, type ProviderEntry } from "@/components/cockpit/deploy/ProviderGrid";
import { EligibilityPanel } from "@/components/cockpit/deploy/EligibilityPanel";
import { PackageMatrix } from "@/components/cockpit/deploy/PackageMatrix";
import { AdvisorChat } from "@/components/cockpit/deploy/AdvisorChat";
import { DispatchConfirm } from "@/components/cockpit/deploy/DispatchConfirm";
import { DemoPaymentModal } from "@/components/cockpit/deploy/DemoPaymentModal";

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

function StepHeader({ id, title, desc }: { id: string; title: string; desc: string }) {
  return (
    <div className="space-y-0.5">
      <h3 className="text-body-sm font-semibold text-on-surface">{id} · {title}</h3>
      <p className="text-caption text-on-surface-variant">{desc}</p>
    </div>
  );
}

export function DeployStudio() {
  const c = useCockpit();
  const [selected, setSelected] = React.useState<string[]>([]);
  const [activeAdvisor, setActiveAdvisor] = React.useState<{ channel: string; lang: string } | null>(null);
  const [paymentOpen, setPaymentOpen] = React.useState(false);
  const [calendar, setCalendar] = React.useState<{ hour: number; blocked: boolean }[]>([]);
  const [dispatch, setDispatch] = React.useState<DispatchSim | null>(null);
  const [dispatching, setDispatching] = React.useState(false);
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

      <div className="min-h-0 flex-1 space-y-6 overflow-auto p-6">
        <section className="space-y-2">
          <StepHeader id="D0" title="발송 채널 선택" desc="발송할 채널을 고르세요. 각 어댑터 상태(stub/live)를 함께 표시합니다." />
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
        </section>

        {c.eligibility && (
          <section className="space-y-2">
            <StepHeader id="D1" title="발송 적법성 (정보통신망법 §50)" desc="수신자별 동의·야간(21~08)·옵트아웃을 판정해 발송대상/제외를 가립니다." />
            <EligibilityPanel total={c.eligibility.total} eligibleCount={c.eligibility.eligible_count} excludedCount={c.eligibility.excluded_count} calendar={calendar} />
          </section>
        )}

        {c.eligibility && matrix.length > 0 && (
          <section className="space-y-2">
            <StepHeader id="D2" title="채널 패키징" desc="선택 채널×언어별로 규격에 맞춰 export 패키지를 생성합니다." />
            <button
              type="button"
              onClick={async () => {
                for (const cell of matrix) {
                  const cp = designCopy[cell.lang] ?? {};
                  const copyText = [cp.headline, cp.body, cp.cta].filter(Boolean).join(" ").trim() || `demo copy ${cell.channel}`;
                  await c.runPackagingCell(cell.channel, cell.lang, copyText, `/runs/${c.runId}/deploy/packages/${cell.channel}_${cell.lang}/visual.png`);
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
          </section>
        )}

        {c.eligibility && (
          <section className="space-y-2">
            <StepHeader id="D3" title="발송 확정" desc="규칙엔진은 자동 발송하지 않습니다 — 최종 발송은 사용자 확정 게이트입니다." />
            <DispatchConfirm
              eligibleCount={c.eligibility.eligible_count}
              selectedCount={selected.length}
              devPass={c.devPass}
              onConfirm={async () => {
                setDispatching(true);
                try {
                  const res = await c.dispatchConfirm();
                  if (res.needsPayment) {
                    setPaymentOpen(true);
                    return;
                  }
                  setDispatch(res as DispatchSim);
                } finally {
                  setDispatching(false);
                }
              }}
              onPayDemo={() => setPaymentOpen(true)}
            />

            {dispatching && (
              <p className="text-caption text-on-surface-variant" role="status" aria-live="polite">
                발송을 처리하고 있습니다…
              </p>
            )}

            {dispatch?.simulation && (
              <div className="space-y-2 rounded-xl border border-outline-variant bg-surface-container-low p-4 animate-fade-in-up" data-testid="dispatch-result">
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
          </section>
        )}
      </div>

      {/* 어드바이저 드로어 (Pro+ 전용 비권위적 조언) */}
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
