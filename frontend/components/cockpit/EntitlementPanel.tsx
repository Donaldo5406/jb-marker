"use client";

import * as React from "react";
import { Crown, Zap } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { cn } from "@/lib/utils";
import { useCockpit } from "./CockpitProvider";

/** Setting 뷰 — Marker 엔타이틀먼트 Free/Pro 토글(Deferral D4: 데모용, 실 PG 청구 없음). */
export function EntitlementPanel() {
  const c = useCockpit();
  const isPro = c.entitlement.marker;
  const [busy, setBusy] = React.useState(false);

  const toggle = async () => {
    setBusy(true);
    try {
      await c.toggleEntitlement();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-surface px-6 py-8">
      <div className="mx-auto w-full max-w-2xl space-y-6">
        <header className="space-y-1">
          <h1 className="text-h3 text-on-surface">설정</h1>
          <p className="text-body-sm text-on-surface-variant">
            데모 엔타이틀먼트를 전환해 Pro 전용 기능을 체험할 수 있습니다.
          </p>
        </header>

        <Card className="space-y-6 p-7">
          <div className="flex items-start gap-4">
            <div
              className={cn(
                "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl",
                isPro ? "bg-primary text-on-primary" : "bg-surface-container text-on-surface-variant",
              )}
            >
              {isPro ? <Crown className="h-5 w-5" aria-hidden /> : <Zap className="h-5 w-5" aria-hidden />}
            </div>

            <div className="min-w-0 flex-1 space-y-1">
              <div className="flex items-center gap-2">
                <h2 className="text-body-lg font-medium text-on-surface">Marker 엔타이틀먼트 (Pro)</h2>
                <span
                  data-testid="entitlement-badge"
                  className={cn(
                    "inline-flex items-center rounded-full px-2.5 py-0.5 text-caption font-medium",
                    isPro
                      ? "bg-primary text-on-primary"
                      : "bg-surface-container-high text-on-surface-variant",
                  )}
                >
                  {isPro ? "Pro" : "Free"}
                </span>
              </div>
              <p className="text-body-sm text-on-surface-variant">
                데모용 엔타이틀먼트(실 PG 청구 없음). ON이면 Marker/Advisor 사용 가능.
              </p>
            </div>

            {/* 토글 스위치 */}
            <button
              type="button"
              role="switch"
              aria-checked={isPro}
              aria-label="Marker 엔타이틀먼트 토글"
              data-testid="entitlement-toggle"
              onClick={() => void toggle()}
              disabled={busy}
              className={cn(
                "relative inline-flex h-7 w-12 shrink-0 items-center rounded-full transition-colors",
                "disabled:cursor-not-allowed disabled:opacity-50",
                isPro ? "bg-primary" : "bg-outline-variant",
              )}
            >
              <span
                className={cn(
                  "inline-block h-5 w-5 transform rounded-full bg-surface-container-lowest shadow-ambient transition-transform",
                  isPro ? "translate-x-6" : "translate-x-1",
                )}
              />
            </button>
          </div>

          <p className="rounded-md border border-outline-variant bg-surface-container-low px-4 py-3 text-caption text-on-surface-variant">
            현재 상태: <span className="font-medium text-on-surface">{isPro ? "Pro (사용 가능)" : "Free (잠김)"}</span>
            {" — "}
            {isPro
              ? "Marker/Advisor 모델로 산출물을 생성할 수 있습니다."
              : "Marker/Advisor 선택 시 업셀 안내가 표시됩니다."}
          </p>
        </Card>

        <Card className="p-7">
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0 flex-1 space-y-1">
              <h2 className="text-body-lg font-medium text-on-surface">Deploy 엔타이틀먼트 (Pro+)</h2>
              <p className="text-body-sm text-on-surface-variant">
                ON이면 Deploy 스튜디오(채널 발송 · §50 적법성 · 발송 어드바이저)를 사용할 수 있습니다. 데모 플래그(실 PG 청구 없음).
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={c.entitlement.deploy}
              aria-label="Deploy 엔타이틀먼트 토글"
              data-testid="deploy-toggle"
              onClick={c.toggleDeploy}
              className={cn(
                "relative inline-flex h-7 w-12 shrink-0 items-center rounded-full transition-colors",
                c.entitlement.deploy ? "bg-primary" : "bg-outline-variant",
              )}
            >
              <span className={cn("inline-block h-5 w-5 transform rounded-full bg-surface-container-lowest shadow-ambient transition-transform", c.entitlement.deploy ? "translate-x-6" : "translate-x-1")} />
            </button>
          </div>
        </Card>
      </div>
    </div>
  );
}
