import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { SessionExpiryBannerView } from "../SessionExpiryBanner";

describe("SessionExpiryBannerView", () => {
  beforeEach(() => { vi.useFakeTimers(); vi.setSystemTime(10_000); });
  afterEach(() => vi.useRealTimers());

  it("healthy(경고 전)면 렌더하지 않는다", () => {
    const { container } = render(<SessionExpiryBannerView
      session={{ status: "active", liveness: "healthy", warnAt: 20_000, suspendAt: 70_000, expiresAt: null }}
      expiredReason={null} onKeepAlive={() => {}} onDismissExpired={() => {}} />);
    expect(container.firstChild).toBeNull();
  });

  it("stalled(warnAt 경과)면 카운트다운 배너를 띄운다", () => {
    render(<SessionExpiryBannerView
      session={{ status: "active", liveness: "stalled", warnAt: 5_000, suspendAt: 70_000, expiresAt: null }}
      expiredReason={null} onKeepAlive={() => {}} onDismissExpired={() => {}} />);
    expect(screen.getByText(/곧 일시중지/)).toBeInTheDocument();
    expect(screen.getByText(/01:00/)).toBeInTheDocument();   // (70000-10000)/1000 = 60s → 01:00
  });

  it("expiredReason이 set이면 만료 안내가 우선 표시된다", () => {
    render(<SessionExpiryBannerView
      session={undefined} expiredReason="retention_elapsed"
      onKeepAlive={() => {}} onDismissExpired={() => {}} />);
    expect(screen.getByText(/만료/)).toBeInTheDocument();
  });
});
