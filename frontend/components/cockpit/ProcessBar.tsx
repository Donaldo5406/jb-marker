"use client";

import { Check, ChevronRight, Lock } from "lucide-react";
import { cn } from "@/lib/utils";
import { STUDIOS, studioNavState, type NavStatus, type Studio } from "@/lib/cockpit-nav";

// STUDIOS 배열(4종 고정)만 셀로 렌더된다 — video는 Studio 타입에만 더해진 제작 슬롯
// 치환값이라 ProcessBar 셀이 아니다. 따라서 LABELS는 전체 Studio 유니온이 아닌
// STUDIOS 원소 타입으로 키잉한다(video 키 불필요).
const LABELS: Record<(typeof STUDIOS)[number], string> = {
  brainstorming: "brainstorming",
  design: "design",
  review: "review",
  deploy: "deploy",
};

/** 단계 상태별 도트(StatusDot 토큰과 일관)·텍스트 톤. */
const DOT_TONE: Record<NavStatus, string> = {
  done: "bg-primary",
  active: "bg-primary animate-pulse",
  pending: "bg-outline-variant",
  blocked: "bg-error",
};

/** review 셀 raw step_status(BLOCKED/WARN/PASS/in_progress) → 색 클래스(M5 §8.1).
 *  review는 일반 NavStatus(done/active/blocked/pending)와 다른 어휘를 갖는다 — 별도 매핑. */
function reviewColorClass(s: string | undefined): string {
  if (s === "BLOCKED") return "bg-severity-critical-bg text-severity-critical-fg border-severity-critical";
  if (s === "WARN") return "bg-severity-warning-bg text-severity-warning-fg border-severity-warning";
  if (s === "PASS") return "bg-severity-ok-bg text-severity-ok-fg border-severity-ok";
  if (s === "in_progress") return "bg-severity-info-bg text-severity-info-fg border-severity-info animate-pulse";
  return "";
}

/** deploy 셀 raw step_status → 색 클래스(M6 T22). review와 동일한 어휘를 공유한다. */
function deployColorClass(s: string | undefined): string {
  if (s === "BLOCKED") return "bg-severity-critical-bg text-severity-critical-fg border-severity-critical";
  if (s === "WARN") return "bg-severity-warning-bg text-severity-warning-fg border-severity-warning";
  if (s === "PASS") return "bg-severity-ok-bg text-severity-ok-fg border-severity-ok";
  if (s === "in_progress") return "bg-severity-info-bg text-severity-info-fg border-severity-info animate-pulse";
  return "";
}

export type ProcessBarProps = {
  stepStatus: Record<string, string>;
  active: Studio;
  onSelect: (s: Studio) => void;
};

/**
 * 4단계 인디케이터 겸 네비게이터.
 * Deferral D8 — M2에서 ProcessBar는 `manifest.step_status`의 **읽기 전용 시각화**다.
 * 완료 판정·set_step_status 쓰기·review→deploy BLOCK 판정은 M3+ 소관.
 * 따라서 모든 탭은 자유롭게 클릭 가능(blocked 포함) — 항상 onSelect 호출.
 */
export function ProcessBar({ stepStatus, active, onSelect }: ProcessBarProps) {
  const nav = studioNavState(stepStatus);

  return (
    <nav
      aria-label="파이프라인 단계"
      className="flex items-center gap-1 border-b border-outline-variant bg-surface-container-low px-4 py-2"
    >
      {STUDIOS.map((s, i) => {
        const status = nav[s];
        const isActive = active === s;
        const blocked = status === "blocked";
        // M5 §8.1: review 셀은 raw step_status(BLOCKED/WARN/PASS/in_progress)에서
        // 별도 색상을 가져온다 — 일반 NavStatus와 어휘가 다름. 매칭 없으면 빈 문자열로 fallback.
        const reviewRaw = s === "review" ? stepStatus.review : undefined;
        const reviewColor = s === "review" ? reviewColorClass(reviewRaw) : "";
        // M6 T22: deploy 셀 색 매핑(review 패턴과 동일 어휘).
        const deployRaw = s === "deploy" ? stepStatus.deploy : undefined;
        const deployColor = s === "deploy" ? deployColorClass(deployRaw) : "";
        return (
          <div key={s} className="flex items-center">
            <button
              type="button"
              data-testid={`step-${s}`}
              data-status={status}
              data-review-status={s === "review" ? (reviewRaw ?? "") : undefined}
              data-deploy-status={s === "deploy" ? (deployRaw ?? "") : undefined}
              aria-current={isActive ? "step" : undefined}
              onClick={() => onSelect(s)}
              className={cn(
                "group inline-flex items-center gap-2 rounded-full border border-transparent px-3 py-1.5 text-body-sm transition-colors",
                isActive
                  ? "bg-surface-container-highest font-medium text-on-surface"
                  : "text-on-surface-variant hover:bg-surface-container",
                // D8: blocked는 잠금 '시각 표현'만 — 흐림 처리하되 클릭은 막지 않음.
                blocked && "opacity-60",
                // M5: review 셀 색 매핑(active 토큰 위에 우선 적용).
                reviewColor,
                // M6 T22: deploy 셀 색 매핑(review와 동일 우선순위).
                deployColor,
              )}
            >
              <span className="flex h-4 w-4 items-center justify-center">
                {status === "done" ? (
                  <Check className="h-3.5 w-3.5 text-primary" aria-label="완료" />
                ) : blocked ? (
                  <Lock className="h-3.5 w-3.5 text-error" aria-label="잠금" />
                ) : (
                  <span className={cn("inline-block h-2 w-2 rounded-full", DOT_TONE[status])} />
                )}
              </span>
              <span className="capitalize">{LABELS[s]}</span>
            </button>
            {i < STUDIOS.length - 1 && (
              <ChevronRight className="mx-0.5 h-4 w-4 shrink-0 text-outline" aria-hidden />
            )}
          </div>
        );
      })}
    </nav>
  );
}
