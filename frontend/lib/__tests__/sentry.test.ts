import { describe, expect, it, vi } from "vitest";

vi.mock("@sentry/browser", () => ({
  init: vi.fn(),
  setTag: vi.fn(),
}));

describe("lib/sentry — DSN 부재 시 no-op", () => {
  it("NEXT_PUBLIC_SENTRY_DSN 없으면 init/setTag를 호출하지 않는다", async () => {
    const Sentry = await import("@sentry/browser");
    const { initSentry, setRunTag } = await import("@/lib/sentry");
    initSentry();
    setRunTag("r1");
    expect(Sentry.init).not.toHaveBeenCalled();
    expect(Sentry.setTag).not.toHaveBeenCalled();
  });
});
