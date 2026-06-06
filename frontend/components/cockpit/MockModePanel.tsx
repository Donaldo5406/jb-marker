"use client";

import * as React from "react";
import { FlaskConical } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { cn } from "@/lib/utils";
import { useCockpit } from "./CockpitProvider";

/** Setting 뷰 — 시연용 Mock(데모) 모드. ON이면 전 스튜디오의 LLM/이미지/비전/advisor가
 *  결정적·무료의 FakeProvider로 동작(요청 단위 플래그, 상태 비영속·라이브 안전).
 *  레포 패턴(view/container 분리)에 따라 View는 props만 받아 테스트 가능. */
export function MockModePanelView({ on, onToggle }: { on: boolean; onToggle: () => void }) {
  return (
    <Card className="p-7">
      <div className="flex items-start gap-4">
        <div
          className={cn(
            "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl",
            on ? "bg-primary text-on-primary" : "bg-surface-container text-on-surface-variant",
          )}
        >
          <FlaskConical className="h-5 w-5" aria-hidden />
        </div>
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex items-center gap-2">
            <h2 className="text-body-lg font-medium text-on-surface">Mock(데모) 모드</h2>
            <span
              data-testid="mock-badge"
              className={cn(
                "inline-flex items-center rounded-full px-2.5 py-0.5 text-caption font-medium",
                on ? "bg-primary text-on-primary" : "bg-surface-container-high text-on-surface-variant",
              )}
            >
              {on ? "ON" : "OFF"}
            </span>
          </div>
          <p className="text-body-sm text-on-surface-variant">
            ON이면 모든 스튜디오가 무료·결정적 더미 응답으로 동작합니다(시연 영상용). 실제 산출물 제작 시 OFF.
          </p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={on}
          aria-label="Mock 모드 토글"
          data-testid="mock-toggle"
          onClick={onToggle}
          className={cn(
            "relative inline-flex h-7 w-12 shrink-0 items-center rounded-full transition-colors",
            on ? "bg-primary" : "bg-outline-variant",
          )}
        >
          <span
            className={cn(
              "inline-block h-5 w-5 transform rounded-full bg-surface-container-lowest shadow-ambient transition-transform",
              on ? "translate-x-6" : "translate-x-1",
            )}
          />
        </button>
      </div>
    </Card>
  );
}

/** Setting에서 사용하는 container — context의 mockMode/setMockMode를 View에 배선. */
export function MockModePanel() {
  const c = useCockpit();
  return <MockModePanelView on={c.mockMode} onToggle={() => c.setMockMode(!c.mockMode)} />;
}
