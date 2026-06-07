"use client";

/** DispatchConfirm (M6 T21) — D3 발송 확정 게이트.
 *  devPass=false 시 결제 모달 트리거 링크 노출. devPass+eligible+selected 모두 충족해야 활성. */
type Props = {
  eligibleCount: number;
  selectedCount: number;
  devPass: boolean;
  onConfirm: () => void;
  onPayDemo: () => void;
};

export function DispatchConfirm({
  eligibleCount,
  selectedCount,
  devPass,
  onConfirm,
  onPayDemo,
}: Props) {
  // devPass는 시각적 힌트(미통과 시 결제 링크 노출) — 실제 게이트는 백엔드 402로 강제.
  // 따라서 dispatch 클릭 가능 여부는 eligible+selected만 본다.
  const canDispatch = eligibleCount > 0 && selectedCount > 0;
  return (
    <div className="border border-outline-variant rounded p-4 space-y-2" data-testid="dispatch-confirm">
      <div className="text-sm">
        발송대상 <b>{eligibleCount}</b>명 · 채널 <b>{selectedCount}</b>개
      </div>
      {!devPass && (
        <button
          type="button"
          onClick={onPayDemo}
          className="text-xs underline text-primary"
        >
          결제 필요 — 데모 결제로 진행
        </button>
      )}
      <button
        type="button"
        disabled={!canDispatch}
        onClick={onConfirm}
        className={
          "w-full py-2 rounded " +
          (canDispatch ? "bg-primary text-on-primary" : "bg-surface-container text-on-surface-variant")
        }
      >
        발송 확정 (시뮬)
      </button>
    </div>
  );
}
