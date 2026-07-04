import { describe, it, expect } from "vitest";
import { iconSrc, ICON_KEYS } from "../iconRegistry";

describe("iconRegistry", () => {
  it("허용 키는 /icons/<key>.svg 경로", () => {
    expect(iconSrc("calendar")).toBe("/icons/calendar.svg");
    expect(ICON_KEYS).toContain("trending-up");
  });
  it("미허용 키는 percent 폴백(임의 파일 참조 방지)", () => {
    expect(iconSrc("../../etc/passwd")).toBe("/icons/percent.svg");
    expect(iconSrc("unknown")).toBe("/icons/percent.svg");
  });
});
