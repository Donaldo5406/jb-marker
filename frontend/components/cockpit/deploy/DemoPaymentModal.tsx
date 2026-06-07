"use client";

/** DemoPaymentModal (M6 T21) — Pro 구독 안내 + 데모 결제(즉시 dev_pass 통과) 버튼.
 *  open=false면 null 반환. demo-pay 클릭 시 onPayDemo 후 onClose. */
type Props = {
  open: boolean;
  onClose: () => void;
  onPayDemo: () => void;
};

export function DemoPaymentModal({ open, onClose, onPayDemo }: Props) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
      data-testid="demo-payment-modal"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="결제"
        className="bg-surface rounded p-6 w-96 space-y-3"
      >
        <h2 className="text-lg font-bold">Pro 구독 (월 $100)</h2>
        <p className="text-sm text-on-surface-variant">Marker 모델 + Advisor 챗 이용권.</p>
        <button
          type="button"
          disabled
          className="w-full py-2 bg-surface-container text-on-surface-variant rounded text-sm"
        >
          결제하기 (M7 활성)
        </button>
        <button
          type="button"
          onClick={() => {
            onPayDemo();
            onClose();
          }}
          className="w-full py-2 bg-primary text-on-primary rounded text-sm"
          data-testid="demo-pay-btn"
        >
          데모 결제 (즉시 통과)
        </button>
        <button
          type="button"
          onClick={onClose}
          className="w-full py-1 text-xs text-on-surface-variant"
        >
          취소
        </button>
      </div>
    </div>
  );
}
