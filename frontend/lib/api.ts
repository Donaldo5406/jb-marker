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
/** HITL 게이트 단일 봉투(T1-P2 §4.4) — kind·actions 항상 포함, None 필드는 wire에서 생략.
 *  ask=brainstorming 질문 / confirm=design 단계 정지 / status=review R3 판정. */
export type GateEnvelope = {
  kind: "ask" | "confirm" | "status";
  actions: string[];
  trigger?: "a" | "b" | "c"; question?: string; options?: string[];
  step?: string; critic?: Record<string, unknown> | null; auto_advanced?: string[];
  status?: "PASS" | "WARN" | "BLOCKED"; critical_count?: number; warning_count?: number;
};
/** confirm 봉투(GateEnvelope)의 CockpitProvider 파생 뷰 — PipelineRail이 소비.
 *  critic은 백엔드 CriticVerdict를 수용하는 방어적 Record(좁히지 말 것). */
export type DesignGate = { step: string; critic: Record<string, unknown> | null; auto_advanced: string[]; actions?: string[] };
/** status 봉투(GateEnvelope)의 CockpitProvider 파생 뷰 — VerdictPanel·Deploy 패널이 소비. */
export type ReviewGate = { status: string; critical: number; warning: number; actions?: string[] };
export type GatewayResult = {
  output_path: string; text: string; gate?: GateEnvelope | null;
  meta?: Record<string, unknown>;
};
export type Provider = "anthropic" | "openai" | "google" | "fake";

// ── session lifecycle (T1 백엔드 계약 미러 — schemas.py:113-158, snake_case 보존) ──
export type SessionLivenessName = "healthy" | "stalled" | "suspended" | "archived" | "transport_dead";
export type SessionStatus = "active" | "suspended" | "archived";
/** heartbeat exists:false — 정확 4키(나머지 키 부재). */
export type SessionMissing = { kind: "heartbeat"; exists: false; status: null; resumable: boolean };
/** heartbeat exists:true — 정확 8키. warn_at/suspend_at/expires_at는 절대 ms epoch. */
export type SessionLiveness = {
  kind: "heartbeat"; exists: true; liveness: SessionLivenessName; status: SessionStatus;
  warn_at: number; suspend_at: number; expires_at: number | null; resumable: boolean;
};
export type SessionHeartbeat = SessionLiveness | SessionMissing;   // exists로 판별
export type SessionRestored = { kind: "restored"; run_id: string; studio: string; status: string };
export type SessionExpired = { kind: "expired"; reason: "no_session" | "retention_elapsed" };
export type SessionResumeResult = SessionRestored | SessionExpired;   // kind로 판별
export type SessionSuspend = { kind: "suspended"; status: string };
export type SessionListItem = { studio: string; status: SessionStatus; updated_at_ms: number; expires_at: number | null };
export type SessionList = { kind: "session_list"; sessions: SessionListItem[] };

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
    provider: Provider; is_marker: boolean; answer?: string | null;
    action?: string | null; bypass_map?: Record<string, boolean> | null;
    mock?: boolean }): Promise<GatewayResult> {
    return j(await authedFetch(`${BASE}/gateway/run`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...p, answer: p.answer ?? null,
        action: p.action ?? null, bypass_map: p.bypass_map ?? null, mock: p.mock ?? false }),
    }));
  },
  async vfsList(runId: string): Promise<{ nodes: VfsNode[] }> {
    return j(await authedFetch(`${BASE}/vfs/${runId}`));
  },
  async vfsGet(runId: string, rest: string): Promise<VfsNode> {
    return j(await authedFetch(`${BASE}/vfs/${runId}/${rest}`));
  },
  async vfsPut(runId: string, rest: string, content: string, mime?: string, contentEncoding?: "base64"): Promise<VfsNode> {
    return j(await authedFetch(`${BASE}/vfs/${runId}/${rest}`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, mime: mime ?? null, content_encoding: contentEncoding ?? null }),
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
  async getGallery(runId: string): Promise<GalleryResponse> {
    return j(await authedFetch(`${BASE}/runs/${runId}/gallery`));
  },
  async getPreviewHtml(runId: string): Promise<string> {
    const r = await authedFetch(`${BASE}/runs/${runId}/preview`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.text();
  },
  async sessionHeartbeat(runId: string, studio: string): Promise<SessionHeartbeat> {
    return j(await authedFetch(`${BASE}/runs/${runId}/session/${studio}`));
  },
  async sessionResume(runId: string, studio: string): Promise<SessionResumeResult> {
    return j(await authedFetch(`${BASE}/runs/${runId}/session/${studio}/resume`, { method: "POST" }));
  },
  async sessionSuspend(runId: string, studio: string): Promise<SessionSuspend> {
    return j(await authedFetch(`${BASE}/runs/${runId}/session/${studio}/suspend`, { method: "POST" }));
  },
  async listSessions(runId: string): Promise<SessionList> {
    return j(await authedFetch(`${BASE}/runs/${runId}/sessions`));
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

export type GalleryItem = {
  path: string; name: string; mime: string | null; source: string | null;
  is_media: boolean; meta: Record<string, unknown>;
};
export type GalleryGroup = { kind: string; items: GalleryItem[] };
export type GallerySection = {
  studio: string; label: string; status: string;
  has_preview: boolean; groups: GalleryGroup[];
};
export type GalleryResponse = {
  run: {
    run_id: string; title: string | null; created_at: string | null;
    current_step: string | null; step_status: Record<string, string>;
    languages: string[];
  };
  sections: GallerySection[];
};
