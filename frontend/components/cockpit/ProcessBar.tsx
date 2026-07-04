"use client";

import { Check, ChevronRight, Clapperboard, ImageIcon, Lock } from "lucide-react";
import { cn } from "@/lib/utils";
import { STUDIOS, productionStudio, studioNavState, type NavStatus, type Studio, type VideoMedium } from "@/lib/cockpit-nav";

const LABELS: Record<Studio, string> = {
  brainstorming: "brainstorming",
  design: "design",
  video: "video",
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
  medium?: VideoMedium;   // 제작 슬롯 스왑(기본 image=design). page가 c.videoMedium 주입.
};

/**
 * 4단계 인디케이터 겸 네비게이터.
 * Deferral D8 — M2에서 ProcessBar는 `manifest.step_status`의 **읽기 전용 시각화**다.
 * 완료 판정·set_step_status 쓰기·review→deploy BLOCK 판정은 M3+ 소관.
 * 따라서 모든 탭은 자유롭게 클릭 가능(blocked 포함) — 항상 onSelect 호출.
 */
export function ProcessBar({ stepStatus, active, onSelect, medium = "image" }: ProcessBarProps) {
  const nav = studioNavState(stepStatus);

  return (
    <nav
      aria-label="파이프라인 단계"
      className="flex items-center gap-1 border-b border-outline-variant bg-surface-container-low px-4 py-2"
    >
      {STUDIOS.map((s, i) => {
        const status = nav[s];
        // 가운데 'design' 셀은 제작 슬롯 — medium으로 design↔video 렌더 치환.
        const isProduction = s === "design";
        const slot: Studio = isProduction ? productionStudio(medium) : s;
        const isActive = active === slot;
        const blocked = status === "blocked";
        // M5 §8.1: review 셀 raw step_status 색상(일반 NavStatus와 어휘 다름).
        const reviewRaw = s === "review" ? stepStatus.review : undefined;
        const reviewColor = s === "review" ? reviewColorClass(reviewRaw) : "";
        // M6 T22: deploy 셀 색 매핑(review 패턴 동일 어휘).
        const deployRaw = s === "deploy" ? stepStatus.deploy : undefined;
        const deployColor = s === "deploy" ? deployColorClass(deployRaw) : "";
        // 슬롯 디자인 A: 제작 슬롯 매체 아이콘(영상=Clapperboard, 이미지=ImageIcon).
        const MediaIcon = slot === "video" ? Clapperboard : ImageIcon;
        return (
          <div key={s} className="flex items-center">
            <button
              type="button"
              data-testid={`step-${slot}`}
              data-status={status}
              data-medium={isProduction ? medium : undefined}
              data-review-status={s === "review" ? (reviewRaw ?? "") : undefined}
              data-deploy-status={s === "deploy" ? (deployRaw ?? "") : undefined}
              aria-current={isActive ? "step" : undefined}
              onClick={() => onSelect(slot)}
              className={cn(
                "group inline-flex items-center gap-2 rounded-full border border-transparent px-3 py-1.5 text-body-sm transition-colors",
                isActive
                  ? "bg-surface-container-highest font-medium text-on-surface"
                  : "text-on-surface-variant hover:bg-surface-container",
                // D8: blocked는 잠금 '시각 표현'만 — 흐림 처리하되 클릭은 막지 않음.
                blocked && "opacity-60",
                // 슬롯 A: 제작 슬롯은 모노크롬 시스템에 맞춰 중립 틴트+인셋 링으로 구분
                // (이질적 보라 #eaddff 제거 — 매체 아이콘이 image↔video 식별자 역할).
                isProduction && !isActive && "bg-surface-container-high text-on-surface ring-1 ring-inset ring-outline-variant hover:bg-surface-container-highest",
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
                  // 모든 셀(제작 슬롯 포함)이 동일한 상태 도트를 쓴다 — active면 펄스(다른 스튜디오와 패턴 일치).
                  <span className={cn("inline-block h-2 w-2 rounded-full", DOT_TONE[status])} />
                )}
              </span>
              {/* 슬롯 A: 제작 슬롯은 매체 식별 아이콘을 라벨 앞에 유지(도트와 별개로 image↔video 시각화). */}
              {isProduction && status !== "done" && status !== "blocked" && (
                <MediaIcon className="h-3.5 w-3.5 text-on-surface-variant" aria-hidden />
              )}
              <span className="capitalize">{LABELS[slot]}</span>
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
