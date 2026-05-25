const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type Manifest = {
  run_id: string; title: string | null; created_at: string | null;
  step_status: Record<string, string>;
};
export type VfsNode = {
  path: string; mime: string | null; source: string | null;
  content_text: string | null; meta: Record<string, unknown>;
};
export type AskPayload = { trigger: "a" | "b" | "c"; question: string; options: string[] };
export type GatewayResult = { output_path: string; text: string; ask?: AskPayload | null };
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
    return j(await fetch(`${BASE}/runs`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: title ?? null }),
    }));
  },
  async listRuns(): Promise<{ runs: Manifest[] }> {
    return j(await fetch(`${BASE}/runs`));
  },
  async gatewayRun(p: { run_id: string; studio: string; prompt: string;
    provider: Provider; is_marker: boolean; answer?: string | null; bypass?: boolean }): Promise<GatewayResult> {
    return j(await fetch(`${BASE}/gateway/run`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...p, answer: p.answer ?? null, bypass: p.bypass ?? false }),
    }));
  },
  async vfsList(runId: string): Promise<{ nodes: VfsNode[] }> {
    return j(await fetch(`${BASE}/vfs/${runId}`));
  },
  async vfsGet(runId: string, rest: string): Promise<VfsNode> {
    return j(await fetch(`${BASE}/vfs/${runId}/${rest}`));
  },
  async vfsPut(runId: string, rest: string, content: string, mime?: string): Promise<VfsNode> {
    return j(await fetch(`${BASE}/vfs/${runId}/${rest}`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, mime: mime ?? null }),
    }));
  },
  async getEntitlement(): Promise<{ marker: boolean }> {
    return j(await fetch(`${BASE}/entitlement`));
  },
  async setEntitlement(marker: boolean): Promise<{ marker: boolean }> {
    return j(await fetch(`${BASE}/entitlement`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ marker }),
    }));
  },
  wsUrl(runId: string): string {
    return `${BASE.replace(/^http/, "ws")}/ws/${runId}`;
  },
};
