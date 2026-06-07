import { describe, it, expect } from "vitest";
import { displayName } from "../fileType";

describe("displayName", () => {
  it(".scene는 '구조화 씬'으로 표기", () => {
    expect(displayName("main.scene")).toBe("구조화 씬");
  });
  it("그 외는 파일명 그대로", () => {
    expect(displayName("report.md")).toBe("report.md");
  });
});
