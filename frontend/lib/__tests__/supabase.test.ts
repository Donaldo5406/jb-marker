import { describe, it, expect, vi, beforeEach } from "vitest";

describe("supabase client", () => {
  beforeEach(() => vi.resetModules());

  it("env 없으면 client=null, getAccessToken=null", async () => {
    delete process.env.NEXT_PUBLIC_SUPABASE_URL;
    delete process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    const mod = await import("../supabase");
    expect(mod.supabase).toBeNull();
    await expect(mod.getAccessToken()).resolves.toBeNull();
  });
});
