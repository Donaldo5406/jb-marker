import { describe, it, expect } from "vitest";
import { studioNavState, STUDIOS } from "../cockpit-nav";

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
