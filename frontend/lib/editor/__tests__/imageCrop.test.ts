import { describe, it, expect } from "vitest";
import { computeAspectCrop } from "../imageCrop";

describe("imageCrop", () => {
  it("free → 전체 복원(크롭 해제)", () => {
    expect(computeAspectCrop(200, 100, "free")).toEqual({ cropX: 0, cropY: 0, width: 200, height: 100 });
  });
  it("1:1 on 200x100 → 중앙 100x100, cropX=50", () => {
    expect(computeAspectCrop(200, 100, "1:1")).toEqual({ cropX: 50, cropY: 0, width: 100, height: 100 });
  });
  it("1:1 on 100x200 → 중앙 100x100, cropY=50", () => {
    expect(computeAspectCrop(100, 200, "1:1")).toEqual({ cropX: 0, cropY: 50, width: 100, height: 100 });
  });
  it("4:5 on 100x100 → width=80, height=100, cropX=10", () => {
    expect(computeAspectCrop(100, 100, "4:5")).toEqual({ cropX: 10, cropY: 0, width: 80, height: 100 });
  });
  it("16:9 on 100x100 → width=100, height=56.25, cropY=21.875", () => {
    const r = computeAspectCrop(100, 100, "16:9");
    expect(r.width).toBe(100);
    expect(r.height).toBeCloseTo(56.25, 5);
    expect(r.cropY).toBeCloseTo(21.875, 5);
    expect(r.cropX).toBe(0);
  });
});
