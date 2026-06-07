"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

const GATES = [
  { id: "S1", label: "Rough", desc: "러프 레이아웃 확정 단계를 자동 통과" },
  { id: "S2a", label: "비주얼", desc: "비주얼 생성 확인을 자동 통과" },
  { id: "S2b", label: "카피", desc: "카피 생성 확인을 자동 통과" },
  { id: "S2c", label: "브랜드", desc: "브랜드 적용 확인을 자동 통과" },
  { id: "S3", label: "Final", desc: "최종 합성 확인을 자동 통과" },
];

export type DesignSettingsProps = {
  bypass: Record<string, boolean>;
  onToggle: (id: string, on: boolean) => void;
};

/** 스킵 스코프 — 단계별 confirm 게이트를 자동 통과할지 선택(드롭다운 패널). */
export function DesignSettings({ bypass, onToggle }: DesignSettingsProps) {
  return (
    <div className="space-y-1 p-4">
      <p className="text-body-sm font-medium text-on-surface">자동 진행(confirm 생략) 범위</p>
      <p className="pb-2 text-caption text-on-surface-variant">켠 단계는 확인 없이 자동 진행됩니다. 끄면 매 단계 확정을 묻습니다.</p>
      {GATES.map((g) => {
        const on = !!bypass[g.id];
        return (
          <div key={g.id} className="flex items-center justify-between gap-3 rounded-lg px-2 py-1.5 hover:bg-surface-container-high">
            <div className="min-w-0">
              <div className="text-body-sm text-on-surface">{g.label}</div>
              <div className="text-caption text-on-surface-variant">{g.desc}</div>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={on}
              aria-label={`${g.label} 자동 진행`}
              data-testid={`bypass-${g.id}`}
              onClick={() => onToggle(g.id, !on)}
              className={cn("relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors", on ? "bg-primary" : "bg-outline-variant")}
            >
              <span className={cn("inline-block h-4 w-4 transform rounded-full bg-surface-container-lowest transition-transform", on ? "translate-x-6" : "translate-x-1")} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
