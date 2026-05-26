export const STUDIOS = ["brainstorming", "design", "review", "deploy"] as const;
export type Studio = (typeof STUDIOS)[number];
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
