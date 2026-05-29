const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

import { getAccessToken } from "./supabase";

/** fetch + Supabase JWT 부착(있을 때만). 로컬/비로그인 모드에선 토큰 null → 헤더 없이 동작. */
export async function authedFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const token = await getAccessToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(input, { ...init, headers });
}

export type Manifest = {
  run_id: string; title: string | null; created_at: string | null;
  step_status: Record<string, string>;
};
export type VfsNode = {
  path: string; mime: string | null; source: string | null;
  content_text: string | null; meta: Record<string, unknown>;
};
export type AskPayload = { trigger: "a" | "b" | "c"; question: string; options: string[] };
export type GatewayResult = {
  output_path: string; text: string; ask?: AskPayload | null;
  meta?: Record<string, unknown>;
};
export type Provider = "anthropic" | "openai" | "google" | "fake";

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const err = new Error(`HTTP ${res.status}`) as Error & { status: number };
    err.status = res.status;
    throw err;
  }
  return res.json() as Promise<T>;
}

export const api = {
  async createRun(title?: string): Promise<{ run_id: string; title: string | null }> {
    return j(await authedFetch(`${BASE}/runs`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: title ?? null }),
    }));
  },
  async listRuns(): Promise<{ runs: Manifest[] }> {
    return j(await authedFetch(`${BASE}/runs`));
  },
  async gatewayRun(p: { run_id: string; studio: string; prompt: string;
    provider: Provider; is_marker: boolean; answer?: string | null; bypass?: boolean;
    action?: string | null }): Promise<GatewayResult> {
    return j(await authedFetch(`${BASE}/gateway/run`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...p, answer: p.answer ?? null, bypass: p.bypass ?? false,
        action: p.action ?? null }),
    }));
  },
  async vfsList(runId: string): Promise<{ nodes: VfsNode[] }> {
    return j(await authedFetch(`${BASE}/vfs/${runId}`));
  },
  async vfsGet(runId: string, rest: string): Promise<VfsNode> {
    return j(await authedFetch(`${BASE}/vfs/${runId}/${rest}`));
  },
  async vfsPut(runId: string, rest: string, content: string, mime?: string): Promise<VfsNode> {
    return j(await authedFetch(`${BASE}/vfs/${runId}/${rest}`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, mime: mime ?? null }),
    }));
  },
  async getEntitlement(): Promise<{ marker: boolean }> {
    return j(await authedFetch(`${BASE}/entitlement`));
  },
  async setEntitlement(marker: boolean): Promise<{ marker: boolean }> {
    return j(await authedFetch(`${BASE}/entitlement`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ marker }),
    }));
  },
  assetUrl(runId: string, rest: string): string {
    return `${BASE}/vfs/${runId}/${rest}`;
  },
  wsUrl(runId: string, token?: string | null): string {
    const base = `${BASE.replace(/^http/, "ws")}/ws/${runId}`;
    return token ? `${base}?token=${encodeURIComponent(token)}` : base;
  },
  async getUsage(runId: string): Promise<UsageSummary> {
    return j(await authedFetch(`${BASE}/runs/${runId}/usage`));
  },
};

export type UsageModelBreakdown = {
  input_tokens: number;
  output_tokens: number;
  images: number;
  cost_usd: number;
  calls: number;
};
export type UsageStepBreakdown = UsageModelBreakdown & {
  by_model: Record<string, UsageModelBreakdown>;
};
export type UsageEntry = {
  ts: number;
  step: string;
  kind: "text" | "vision" | "image";
  model: string;
  input_tokens: number;
  output_tokens: number;
  images: number;
  cost_usd: number;
  known_model: boolean;
  meta: Record<string, unknown>;
};
export type UsageSummary = {
  total: UsageModelBreakdown;
  by_step: Record<string, UsageStepBreakdown>;
  entries: UsageEntry[];
};
