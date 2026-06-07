import * as React from "react";
import { cn } from "@/lib/utils";

export type DeployCardProps = {
  step?: string;
  title: string;
  desc?: string;
  badge?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
};

/** Deploy 스튜디오 공용 카드 셸 — step 칩 + 제목 + 설명 + 우측 badge 슬롯. 순수 표현(클라 지시자 불필요). */
export function DeployCard({ step, title, desc, badge, children, className }: DeployCardProps) {
  return (
    <section
      data-testid="deploy-card"
      className={cn(
        "rounded-2xl border border-outline-variant bg-surface-container-lowest p-5 shadow-ambient",
        className,
      )}
    >
      <header className="mb-3 flex items-start justify-between gap-3">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            {step && (
              <span className="rounded-md bg-surface-container px-1.5 py-0.5 font-mono text-caption text-on-surface-variant">
                {step}
              </span>
            )}
            <h3 className="text-body-sm font-semibold text-on-surface">{title}</h3>
          </div>
          {desc && <p className="text-caption text-on-surface-variant">{desc}</p>}
        </div>
        {badge && <div className="shrink-0">{badge}</div>}
      </header>
      {children}
    </section>
  );
}
