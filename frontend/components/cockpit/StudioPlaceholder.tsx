"use client";

import { Hammer } from "lucide-react";

/** 스튜디오별 도입 마일스톤(Deferral D1). */
const MILESTONE: Record<string, string> = {
  design: "M4",
  review: "M5",
  deploy: "M6",
};

const LABEL: Record<string, string> = {
  design: "디자인",
  review: "검토",
  deploy: "발송",
};

export type StudioPlaceholderProps = { studio: string };

/** design/review/deploy 탭 본문 — "준비 중" 안내(Deferral D1). */
export function StudioPlaceholder({ studio }: StudioPlaceholderProps) {
  const milestone = MILESTONE[studio] ?? "후속";
  const label = LABEL[studio] ?? studio;
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 bg-surface px-8 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-outline-variant bg-surface-container-lowest">
        <Hammer className="h-5 w-5 text-outline" aria-hidden />
      </div>
      <p className="text-body-lg font-medium text-on-surface">준비 중</p>
      <p className="max-w-sm text-body-sm text-on-surface-variant">
        <span className="font-medium text-on-surface">{label}</span> 스튜디오({studio})는 {milestone}에서
        제공됩니다.
      </p>
    </div>
  );
}
