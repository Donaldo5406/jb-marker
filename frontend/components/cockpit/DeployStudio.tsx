"use client";
import { useState } from "react";
import { useCockpit } from "@/components/cockpit/CockpitProvider";
import { ProviderGrid, type ProviderEntry } from "@/components/cockpit/deploy/ProviderGrid";
import { EligibilityPanel } from "@/components/cockpit/deploy/EligibilityPanel";
import { PackageMatrix } from "@/components/cockpit/deploy/PackageMatrix";
import { AdvisorChat } from "@/components/cockpit/deploy/AdvisorChat";
import { DispatchConfirm } from "@/components/cockpit/deploy/DispatchConfirm";
import { DemoPaymentModal } from "@/components/cockpit/deploy/DemoPaymentModal";

/** DeployStudio (M6 T21) — D0~D3 통합 패널.
 *  D0 채널 선택 → D1 적법성 → D2 패키징 → D3 발송 확정. 결제 게이트 시 DemoPaymentModal. */

const SEED_PROVIDERS: ProviderEntry[] = [
  { id: "email", name: "이메일", logo_path: "/providers/email.svg", channel_type: "email", adapter_status: "stub", priority: 1 },
  { id: "kakao", name: "카카오 알림톡", logo_path: "/providers/kakao.svg", channel_type: "messenger", adapter_status: "stub", priority: 2 },
  { id: "sms", name: "SMS", logo_path: "/providers/sms.svg", channel_type: "sms", adapter_status: "stub", priority: 3 },
  { id: "naver", name: "네이버 광고", logo_path: "/providers/naver.svg", channel_type: "ad", adapter_status: "stub", priority: 4 },
  { id: "google", name: "구글 광고", logo_path: "/providers/google.svg", channel_type: "ad", adapter_status: "stub", priority: 5 },
  { id: "instagram", name: "인스타그램", logo_path: "/providers/instagram.svg", channel_type: "social", adapter_status: "stub", priority: 6 },
];

export function DeployStudio() {
  const c = useCockpit();
  const [selected, setSelected] = useState<string[]>([]);
  const [activeAdvisor, setActiveAdvisor] = useState<{ channel: string; lang: string } | null>(null);
  const [paymentOpen, setPaymentOpen] = useState(false);
  const [calendar, setCalendar] = useState<{ hour: number; blocked: boolean }[]>([]);

  // manifest에 languages가 없을 경우 ko 기본(M6 spec — design _state.json 출처는 별도 fetch).
  const languages: string[] = ["ko"];
  const matrix: { channel: string; lang: string }[] = selected.flatMap((ch) =>
    languages.map((l) => ({ channel: ch, lang: l })),
  );

  return (
    <div className="space-y-4 p-4 col-span-2 overflow-auto" data-testid="deploy-studio">
      <section>
        <h3 className="text-sm font-bold mb-2">D0 채널 선택</h3>
        <ProviderGrid providers={SEED_PROVIDERS} selected={selected} onChange={setSelected} />
        <button
          type="button"
          onClick={async () => {
            await c.setupDeploy(selected, languages);
            await c.runEligibility();
            // 캘린더는 별도 fetch가 없으면 night 기본값(21시-7시 차단).
            setCalendar(Array.from({ length: 24 }, (_, h) => ({ hour: h, blocked: h >= 21 || h < 8 })));
          }}
          disabled={selected.length === 0}
          className="mt-2 px-3 py-1 bg-blue-500 text-white rounded text-sm disabled:bg-gray-300"
        >
          적법성 검사 실행
        </button>
      </section>

      {c.eligibility && (
        <section>
          <h3 className="text-sm font-bold mb-2">D1 발송 적법성</h3>
          <EligibilityPanel
            total={c.eligibility.total}
            eligibleCount={c.eligibility.eligible_count}
            excludedCount={c.eligibility.excluded_count}
            calendar={calendar}
          />
        </section>
      )}

      {c.eligibility && matrix.length > 0 && (
        <section>
          <h3 className="text-sm font-bold mb-2">D2 패키징</h3>
          <button
            type="button"
            onClick={async () => {
              for (const cell of matrix) {
                await c.runPackagingCell(
                  cell.channel,
                  cell.lang,
                  "demo copy " + cell.channel,
                  `/runs/${c.runId}/deploy/packages/${cell.channel}_${cell.lang}/visual.png`,
                );
              }
            }}
            className="mb-2 px-3 py-1 bg-blue-500 text-white rounded text-sm"
          >
            전체 패키징 실행
          </button>
          <PackageMatrix
            cells={matrix.map((m) => ({
              ...m,
              ...(c.packages[`${m.channel}_${m.lang}`] ?? {}),
            }))}
            onAskAdvisor={(channel, lang) => setActiveAdvisor({ channel, lang })}
          />
          {activeAdvisor && (
            <div className="mt-3">
              <AdvisorChat
                packageId={`${activeAdvisor.channel}_${activeAdvisor.lang}`}
                onSubmit={(msg) =>
                  c.askAdvisor(`${activeAdvisor.channel}_${activeAdvisor.lang}`, msg)
                }
                onPayDemo={() => setPaymentOpen(true)}
              />
            </div>
          )}
        </section>
      )}

      {c.eligibility && (
        <section>
          <h3 className="text-sm font-bold mb-2">D3 발송 확정</h3>
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
        </section>
      )}

      <DemoPaymentModal
        open={paymentOpen}
        onClose={() => setPaymentOpen(false)}
        onPayDemo={() => {
          void c.payDemo();
        }}
      />
    </div>
  );
}
