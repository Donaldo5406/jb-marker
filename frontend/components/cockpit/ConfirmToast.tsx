"use client";

import { AlertTriangle, X } from "lucide-react";

/** 비차단 확인 토스트(작업 손실 경고 등). open=false면 미렌더.
 *  AskUserToast와 동일한 하단-중앙 오버레이 스타일, 단 자유 입력 없이 확정/취소 2버튼. */
export function ConfirmToastView({
  open,
  message,
  confirmLabel = "이동",
  cancelLabel = "취소",
  onConfirm,
  onCancel,
}: {
  open: boolean;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-6 z-40 flex justify-center px-4">
      <div
        role="alertdialog"
        aria-labelledby="confirm-toast-msg"
        className="pointer-events-auto w-full max-w-md rounded-2xl border border-severity-warning bg-surface-container-lowest p-4 shadow-ambient animate-fade-in-up"
      >
        <div className="flex items-start gap-2">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-severity-warning" aria-hidden />
          <p id="confirm-toast-msg" className="flex-1 text-body-sm font-medium text-on-surface">
            {message}
          </p>
          <button
            type="button"
            onClick={onCancel}
            aria-label="닫기"
            className="text-on-surface-variant hover:text-on-surface"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>
        <div className="mt-3 flex justify-end gap-2 pl-6">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-full border border-outline-variant px-3 py-1.5 text-caption font-medium text-on-surface-variant transition-colors hover:bg-surface-container-high"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-full bg-primary px-3 py-1.5 text-caption font-medium text-on-primary transition-colors hover:bg-primary-container"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
