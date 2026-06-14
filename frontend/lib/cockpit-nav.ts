export const STUDIOS = ["brainstorming", "design", "review", "deploy"] as const;
/** nav 제작 슬롯은 매체로 design↔video 스왑된다. STUDIOS 배열은 4종 고정(계약 테스트 불변)이고,
 *  video는 타입에만 더한다 — 제작 셀은 렌더 치환(productionStudio)으로 처리. */
export type Studio = (typeof STUDIOS)[number] | "video";
export type VideoMedium = "image" | "video";

/** 가운데 '제작' 슬롯이 가리키는 실제 스튜디오 — 매체 토글로 결정. */
export function productionStudio(medium: VideoMedium): Studio {
  return medium === "video" ? "video" : "design";
}

/** 세션 수명주기 대상 스튜디오 — 백엔드 LIFECYCLE_STUDIOS(vfs/types.py:9)와 정합.
 *  nav STUDIOS(4종)와 별개: 영상 모듈 머지로 video가 추가된 5종. 세션 목록/heartbeat가 다룸. */
export const LIFECYCLE_STUDIOS = ["brainstorming", "design", "review", "video", "deploy"] as const;
export type LifecycleStudio = (typeof LIFECYCLE_STUDIOS)[number];
export type NavStatus = "done" | "active" | "pending" | "blocked";

/** manifest.step_status → 4단계 시각 상태. 미정 단계는 pending.
 *  M2는 읽기 전용 시각화(Deferral D8): 완료 판정·set_step_status 쓰기는 M3+. */
export function studioNavState(stepStatus: Record<string, string>): Record<Studio, NavStatus> {
  const map = {} as Record<Studio, NavStatus>;
  for (const s of STUDIOS) {
    const v = stepStatus[s];
    map[s] =
      v === "done" ? "done"
      : v === "active" ? "active"
      : v === "blocked" ? "blocked"
      : "pending";
  }
  return map;
}

/** Deploy 잠금 해제 술어 — M5 spec §7.2.
 *  PASS = 무조건 해제 / WARN = ack 후 해제 / BLOCKED·pending = 잠금. */
export interface DeployUnlockManifest {
  step_status?: { review?: string } & Record<string, string>;
}
export interface DeployUnlockReviewState {
  acknowledged?: boolean;
}

export function isDeployUnlocked(
  manifest: DeployUnlockManifest,
  reviewState?: DeployUnlockReviewState
): boolean {
  const s = manifest.step_status?.review;
  if (s === "PASS") return true;
  if (s === "WARN" && reviewState?.acknowledged === true) return true;
  return false;
}

export type FilePlacement = "inline" | "center" | "drawer";

/** openFile 표면 결정: brainstorming=인라인 / Design의 .scene=중앙 / 그 외=드로어. */
export function filePlacement(studio: Studio, path: string | null): FilePlacement {
  if (!path) return "inline";
  if (studio === "brainstorming") return "inline";
  if (studio === "design" && path.endsWith(".scene")) return "center";
  return "drawer";
}

export type NavSignals = {
  brainDone: boolean;
  designDone: boolean;
  videoDone?: boolean;      // 제작 슬롯이 video일 때의 완료 신호(videoStep==="done")
  medium?: VideoMedium;     // 'video'면 제작 슬롯=video, 미지정/'image'면 design(기본)
  reviewStatus?: string; // "PASS" | "WARN" | "BLOCKED" | ...
  reviewAcknowledged: boolean;
};
export type NavSuggestion = {
  target: Studio;
  direction: "forward" | "back";
  label: string;
};

/** 현재 활성 스튜디오 맥락에서 권유할 다음 이동(없으면 null).
 *  제작 슬롯은 medium으로 design XOR video. 토스트 중복 노출 방지는 호출 측(StudioNavToast)이 처리. */
export function deriveNavSuggestion(s: NavSignals, active: Studio): NavSuggestion | null {
  const production = productionStudio(s.medium ?? "image");
  const productionDone = production === "video" ? !!s.videoDone : s.designDone;
  const productionName = production === "video" ? "Video" : "Design";
  if (active === "review") {
    if (s.reviewStatus === "BLOCKED")
      return { target: production, direction: "back", label: `critical 위반 — ${productionName}에서 수정 후 재검토` };
    if (s.reviewStatus === "PASS" || (s.reviewStatus === "WARN" && s.reviewAcknowledged))
      return { target: "deploy", direction: "forward", label: "Deploy 스튜디오로 이동" };
    return null;
  }
  if (active === production && productionDone)
    return { target: "review", direction: "forward", label: "Review 스튜디오로 이동" };
  if (active === "brainstorming" && s.brainDone)
    return { target: production, direction: "forward", label: `${productionName} 스튜디오로 이동` };
  return null;
}
