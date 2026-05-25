"use client";

import * as React from "react";

const GATES = [
  { id: "S1", label: "Rough" },
  { id: "S2a", label: "비주얼" },
  { id: "S2b", label: "카피" },
  { id: "S2c", label: "브랜드" },
  { id: "S3", label: "Final" },
];

export type DesignSettingsProps = {
  bypass: Record<string, boolean>;
  onToggle: (id: string, on: boolean) => void;
};

/** 단계별 confirm 게이트 bypass(자동 진행) 토글.
 *  M4: 선호를 CockpitProvider→gateway→harness `_state.json["bypass"]`에 영속화(게이트 의미론은 유보). */
export function DesignSettings({ bypass, onToggle }: DesignSettingsProps) {
  return (
    <div className="space-y-2 p-4">
      <p className="text-body-sm font-medium text-on-surface">자동 진행(confirm 생략)</p>
      {GATES.map((g) => (
        <label
          key={g.id}
          className="flex items-center justify-between text-caption text-on-surface-variant"
        >
          <span>{g.label}</span>
          <input
            type="checkbox"
            checked={!!bypass[g.id]}
            onChange={(e) => onToggle(g.id, e.target.checked)}
          />
        </label>
      ))}
    </div>
  );
}
