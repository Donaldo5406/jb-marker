import { describe, it, expect } from "vitest";
import { filePlacement, deriveNavSuggestion } from "../cockpit-nav";

describe("filePlacement", () => {
  it("brainstorming은 항상 inline", () => {
    expect(filePlacement("brainstorming", "/r/brainstorming/x.md")).toBe("inline");
  });
  it("design의 .scene은 center, 그 외는 drawer", () => {
    expect(filePlacement("design", "/r/design/final/ko/main.scene")).toBe("center");
    expect(filePlacement("design", "/r/design/rough/layout.spec.json")).toBe("drawer");
  });
  it("review/deploy의 모든 파일은 drawer", () => {
    expect(filePlacement("review", "/r/review/report.md")).toBe("drawer");
    expect(filePlacement("deploy", "/r/deploy/x.png")).toBe("drawer");
  });
  it("path 없으면 inline", () => {
    expect(filePlacement("design", null)).toBe("inline");
  });
});

describe("deriveNavSuggestion", () => {
  const base = { brainDone: false, designDone: false, reviewStatus: undefined, reviewAcknowledged: false };
  it("brain done + brainstorming 활성 → design 권유", () => {
    const s = deriveNavSuggestion({ ...base, brainDone: true }, "brainstorming");
    expect(s).toEqual({ target: "design", direction: "forward", label: "Design 스튜디오로 이동" });
  });
  it("design done + design 활성 → review 권유", () => {
    const s = deriveNavSuggestion({ ...base, designDone: true }, "design");
    expect(s?.target).toBe("review");
  });
  it("review BLOCKED + review 활성 → design 복귀(back)", () => {
    const s = deriveNavSuggestion({ ...base, reviewStatus: "BLOCKED" }, "review");
    expect(s).toEqual({ target: "design", direction: "back", label: "critical 위반 — Design에서 수정 후 재검토" });
  });
  it("review PASS + review 활성 → deploy 권유", () => {
    expect(deriveNavSuggestion({ ...base, reviewStatus: "PASS" }, "review")?.target).toBe("deploy");
  });
  it("review WARN은 ack 전엔 null, ack 후 deploy 권유", () => {
    expect(deriveNavSuggestion({ ...base, reviewStatus: "WARN" }, "review")).toBeNull();
    expect(deriveNavSuggestion({ ...base, reviewStatus: "WARN", reviewAcknowledged: true }, "review")?.target).toBe("deploy");
  });
  it("다른 스튜디오 활성 중엔 권유하지 않음(맥락 한정)", () => {
    expect(deriveNavSuggestion({ ...base, brainDone: true }, "design")).toBeNull();
  });
});
