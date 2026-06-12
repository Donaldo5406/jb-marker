import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@sentry/browser", () => ({
  init: vi.fn(),
  setTag: vi.fn(),
}));

beforeEach(() => {
  vi.resetModules();
  vi.clearAllMocks();
});

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

describe("lib/sentry — DSN 있으면 동작", () => {
  it("init 1회 + setTag 전달 + 중복 init 방지", async () => {
    vi.stubEnv("NEXT_PUBLIC_SENTRY_DSN", "https://k@o0.ingest.sentry.io/1");
    const Sentry = await import("@sentry/browser");
    const { initSentry, setRunTag } = await import("@/lib/sentry");
    initSentry();
    initSentry();
    setRunTag("r1");
    expect(Sentry.init).toHaveBeenCalledTimes(1);
    expect(Sentry.init).toHaveBeenCalledWith({ dsn: "https://k@o0.ingest.sentry.io/1" });
    expect(Sentry.setTag).toHaveBeenCalledWith("run_id", "r1");
    vi.unstubAllEnvs();
  });
});
