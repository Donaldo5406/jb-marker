import { describe, it, expect } from "vitest";
import { isDeployUnlocked } from "../lib/cockpit-nav";

describe("isDeployUnlocked", () => {
  it("PASS → unlock", () => {
    expect(isDeployUnlocked({ step_status: { review: "PASS" } }, { acknowledged: false })).toBe(true);
  });
  it("WARN + acked → unlock", () => {
    expect(isDeployUnlocked({ step_status: { review: "WARN" } }, { acknowledged: true })).toBe(true);
  });
  it("WARN + 미ack → lock", () => {
    expect(isDeployUnlocked({ step_status: { review: "WARN" } }, { acknowledged: false })).toBe(false);
  });
  it("BLOCKED → lock(ack 무관)", () => {
    expect(isDeployUnlocked({ step_status: { review: "BLOCKED" } }, { acknowledged: true })).toBe(false);
  });
  it("pending → lock", () => {
    expect(isDeployUnlocked({ step_status: {} }, { acknowledged: false })).toBe(false);
  });
});
