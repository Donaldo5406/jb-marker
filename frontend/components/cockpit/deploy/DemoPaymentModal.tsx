"use client";

import { useEffect, useState } from "react";
import { CreditCard, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/Button";

/** DemoPaymentModal (M6 T21) — Pro+ 구독 안내 + 데모 결제(즉시 dev_pass 통과).
 *  open=false면 null. demo-pay 클릭 시 onPayDemo(완료 대기) 후 onClose.
 *  디자인 시스템 정렬(UpsellModal 패턴): backdrop-blur·elev-4·아이콘·토큰 타입·공용 Button·Esc. */
type Props = {
  open: boolean;
  onClose: () => void;
  onPayDemo: () => void | Promise<unknown>;
};

export function DemoPaymentModal({ open, onClose, onPayDemo }: Props) {
  const [paying, setPaying] = useState(false);

  // a11y: 열려 있을 때 Esc로 닫기(결제 중에는 무시).
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !paying) onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, paying, onClose]);

  if (!open) return null;

  return (
    <div
      data-testid="demo-payment-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="demo-pay-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <button
        type="button"
        aria-label="닫기"
        onClick={() => !paying && onClose()}
        className="absolute inset-0 bg-on-surface/20 backdrop-blur-sm"
      />
      <div className="relative z-10 w-full max-w-sm animate-fade-in-up rounded-[24px] border border-outline-variant bg-surface-container-lowest p-7 shadow-elev-4">
        <button
          type="button"
          onClick={onClose}
          disabled={paying}
          aria-label="닫기"
          className="absolute right-4 top-4 inline-flex h-8 w-8 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface disabled:opacity-40"
        >
          <X className="h-4 w-4" aria-hidden />
        </button>

        <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-on-primary shadow-elev-1">
          <CreditCard className="h-5 w-5" aria-hidden />
        </div>

        <h2 id="demo-pay-title" className="text-h3 text-on-surface">
          Pro+ 구독 · 월 ₩150,000
        </h2>
        <p className="mt-2 text-body-sm text-on-surface-variant">
          Deploy 스튜디오(채널 발송 · §50 적법성 판정 · 발송 어드바이저) 이용권입니다.
        </p>

        <div className="mt-6 flex flex-col gap-2">
          <Button
            variant="primary"
            data-testid="demo-pay-btn"
            disabled={paying}
            onClick={async () => {
              setPaying(true);
              try {
                await onPayDemo();
                onClose();
              } finally {
                setPaying(false);
              }
            }}
            className="w-full"
          >
            {paying && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />}
            {paying ? "결제 처리 중…" : "데모 결제 (즉시 통과)"}
          </Button>
          <Button variant="secondary" onClick={onClose} disabled={paying} className="w-full">
            취소
          </Button>
        </div>

        <p className="mt-3 text-center text-caption text-on-surface-variant">
          실 PG 연동은 준비 중 · 데모 결제는 실 청구 없이 즉시 통과됩니다.
        </p>
      </div>
    </div>
  );
}
