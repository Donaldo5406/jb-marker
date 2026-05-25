"use client";

import { useEffect } from "react";
import { Lock, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useCockpit } from "./CockpitProvider";

/** 402(Marker/Advisor + 무료) 수신 시 표시되는 업셀 모달.
 *  Provider.upsellOpen이 true일 때만 렌더. Auralis 라이트 오버레이. */
export function UpsellModal() {
  const c = useCockpit();
  const { upsellOpen, closeUpsell } = c;

  // a11y: 모달이 열려 있을 때 Esc로 닫기(언마운트/닫힘 시 리스너 정리).
  useEffect(() => {
    if (!upsellOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeUpsell();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [upsellOpen, closeUpsell]);

  if (!upsellOpen) return null;

  const goSetting = () => {
    c.setView("setting");
    c.closeUpsell();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="upsell-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      {/* 라이트 오버레이 */}
      <button
        type="button"
        aria-label="닫기"
        onClick={c.closeUpsell}
        className="absolute inset-0 bg-on-surface/20 backdrop-blur-sm"
      />
      <div className="relative z-10 w-full max-w-sm animate-fade-in-up rounded-[24px] border border-outline-variant bg-surface-container-lowest p-7 shadow-ambient">
        <button
          type="button"
          onClick={c.closeUpsell}
          aria-label="닫기"
          className="absolute right-4 top-4 inline-flex h-8 w-8 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface"
        >
          <X className="h-4 w-4" aria-hidden />
        </button>

        <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-on-primary">
          <Lock className="h-5 w-5" aria-hidden />
        </div>

        <h2 id="upsell-title" className="text-h3 text-on-surface">
          Pro 전용 기능입니다
        </h2>
        <p className="mt-2 text-body-sm text-on-surface-variant">
          Marker/Advisor는 Pro($100/월) 전용입니다. 데모에서는 Setting에서 엔타이틀먼트를 토글해 체험할 수
          있습니다.
        </p>

        <div className="mt-6 flex flex-col gap-2">
          <Button variant="primary" onClick={goSetting}>
            Setting에서 데모 토글
          </Button>
          <Button variant="secondary" onClick={c.closeUpsell}>
            닫기
          </Button>
        </div>
      </div>
    </div>
  );
}
