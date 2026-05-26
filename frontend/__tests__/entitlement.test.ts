import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchDeployState, payDemo, isUnlocked } from "@/lib/entitlement";

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("entitlement helpers", () => {
  it("isUnlocked true when dev_pass=true", () => {
    expect(isUnlocked({ step_status: "x", selected_providers: [], matrix: [], dev_pass: true })).toBe(true);
  });

  it("isUnlocked false when dev_pass=false", () => {
    expect(isUnlocked({ step_status: "x", selected_providers: [], matrix: [], dev_pass: false })).toBe(false);
  });

  it("fetchDeployState parses response", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ step_status: "in_progress", selected_providers: ["email"], matrix: [], dev_pass: false }),
    } as any);
    const s = await fetchDeployState("r1");
    expect(s.selected_providers).toEqual(["email"]);
  });

  it("payDemo POSTs and returns dev_pass", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ dev_pass: true }) } as any);
    const res = await payDemo("r1");
    expect(res.dev_pass).toBe(true);
  });
});
