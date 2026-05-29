/** entitlement helpers (M6 T18) — /deploy/_state · /deploy/demo-payment 헬퍼.
 *  CockpitProvider deploy 액션이 직접 fetch 하므로 이 모듈은 외부(테스트·페이지) 헬퍼용. */

import { authedFetch } from "./api";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type DeployState = {
  step_status: string;
  selected_providers: string[];
  matrix: { channel: string; lang: string }[];
  dev_pass: boolean;
};

export async function fetchDeployState(runId: string): Promise<DeployState> {
  const res = await authedFetch(`${BASE}/runs/${runId}/deploy/_state`);
  if (!res.ok) throw new Error(`deploy state fetch failed: ${res.status}`);
  return res.json();
}

export async function payDemo(runId: string): Promise<{ dev_pass: boolean }> {
  const res = await authedFetch(`${BASE}/runs/${runId}/deploy/demo-payment`, { method: "POST" });
  if (!res.ok) throw new Error("demo payment failed");
  return res.json();
}

export function isUnlocked(state: DeployState): boolean {
  return state.dev_pass === true;
}
