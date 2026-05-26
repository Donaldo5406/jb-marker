import * as React from "react";
import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { CockpitProvider, useCockpit } from "@/components/cockpit/CockpitProvider";

/** WebSocket noop — CockpitProvider 내부 useRunSocket가 jsdom에서 throw하지 않도록. */
class NoopWS {
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
  constructor(public url: string) {}
}

describe("CockpitProvider deploy actions", () => {
  beforeEach(() => {
    (global as any).WebSocket = NoopWS as any;
    global.fetch = vi.fn().mockImplementation((url: string) => {
      const u = String(url);
      if (u.includes("/deploy/eligibility")) {
        return Promise.resolve({ ok: true, status: 200, json: async () => ({ total: 512, eligible_count: 100, excluded_count: 412 }) });
      }
      if (u.includes("/deploy/dispatch")) {
        return Promise.resolve({ ok: false, status: 402, json: async () => ({}) });
      }
      if (u.includes("/deploy/demo-payment")) {
        return Promise.resolve({ ok: true, status: 200, json: async () => ({ dev_pass: true }) });
      }
      // entitlement init + runs list 등 다른 호출 무해 처리.
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
    });
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <CockpitProvider runId="r1">{children}</CockpitProvider>
  );

  it("runEligibility populates eligibility state", async () => {
    const { result } = renderHook(() => useCockpit(), { wrapper });
    await act(async () => {
      await result.current.runEligibility();
    });
    await waitFor(() => expect(result.current.eligibility?.total).toBe(512));
  });

  it("dispatchConfirm returns needsPayment when 402", async () => {
    const { result } = renderHook(() => useCockpit(), { wrapper });
    let out: { needsPayment?: boolean } = {};
    await act(async () => {
      out = await result.current.dispatchConfirm();
    });
    expect(out.needsPayment).toBe(true);
  });

  it("payDemo sets devPass true", async () => {
    const { result } = renderHook(() => useCockpit(), { wrapper });
    await act(async () => {
      await result.current.payDemo();
    });
    await waitFor(() => expect(result.current.devPass).toBe(true));
  });
});
