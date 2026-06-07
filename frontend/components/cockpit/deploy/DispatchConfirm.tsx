"use client";

/** DispatchConfirm (M6 T21) — D3 발송 확정 게이트.
 *  devPass=false 시 결제 모달 트리거 링크 노출. dispatch 클릭 가능 여부는 eligible+selected만 본다
 *  (실제 결제 게이트는 백엔드 402로 강제). */
type Props = {
  eligibleCount: number;
  selectedCount: number;
  devPass: boolean;
  onConfirm: () => void;
  onPayDemo: () => void;
};

export function DispatchConfirm({ eligibleCount, selectedCount, devPass, onConfirm, onPayDemo }: Props) {
  const canDispatch = eligibleCount > 0 && selectedCount > 0;
  return (
    <div className="space-y-3" data-testid="dispatch-confirm">
      <div className="flex items-center gap-3 text-body-sm text-on-surface">
        <span>발송대상 <b className="tabular-nums">{eligibleCount}</b>명</span>
        <span className="text-outline">·</span>
        <span>채널 <b className="tabular-nums">{selectedCount}</b>개</span>
      </div>
      {!devPass && (
        <button type="button" onClick={onPayDemo} className="text-caption font-medium text-primary underline">
          결제 필요 — 데모 결제로 진행
        </button>
      )}
      <button
        type="button"
        disabled={!canDispatch}
        onClick={onConfirm}
        className={
          "w-full rounded-lg py-2 text-body-sm font-medium " +
          (canDispatch ? "bg-primary text-on-primary hover:bg-primary-container" : "bg-surface-container text-on-surface-variant")
        }
      >
        발송 확정 (시뮬)
      </button>
    </div>
  );
}
