import { describe, it, expect } from "vitest";
import { studioNavState, STUDIOS, LIFECYCLE_STUDIOS } from "../cockpit-nav";

describe("studioNavState", () => {
  it("status가 done이면 done, 미정이면 pending", () => {
    const s = studioNavState({ brainstorming: "done" });
    expect(s.brainstorming).toBe("done");
    expect(s.design).toBe("pending");
  });
  it("blocked는 잠금으로 표기", () => {
    const s = studioNavState({ deploy: "blocked" });
    expect(s.deploy).toBe("blocked");
  });
  it("STUDIOS 4단계를 모두 포함", () => {
    const s = studioNavState({});
    expect(Object.keys(s).sort()).toEqual([...STUDIOS].sort());
  });
});

describe("LIFECYCLE_STUDIOS (세션 수명주기 5종)", () => {
  it("백엔드 vfs/types.py LIFECYCLE_STUDIOS와 정합 — video 포함 5종", () => {
    expect([...LIFECYCLE_STUDIOS]).toEqual([
      "brainstorming", "design", "review", "video", "deploy",
    ]);
  });
});
