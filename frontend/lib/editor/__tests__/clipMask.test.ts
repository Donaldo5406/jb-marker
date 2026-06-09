import { describe, it, expect } from "vitest";
import { buildClipPath, maskKindOf } from "../clipMask";

const ctors = {
  Rect: class { type = "rect"; props: any; constructor(o: any) { this.props = o; Object.assign(this, o); } },
  Ellipse: class { type = "ellipse"; props: any; constructor(o: any) { this.props = o; Object.assign(this, o); } },
} as any;

describe("clipMask", () => {
  it("none → null", () => {
    expect(buildClipPath("none", { width: 100, height: 100 }, ctors)).toBeNull();
  });
  it("rounded → Rect, rx>0 + 중심 정렬", () => {
    const cp: any = buildClipPath("rounded", { width: 200, height: 100 }, ctors);
    expect(cp.type).toBe("rect");
    expect(cp.width).toBe(200); expect(cp.height).toBe(100);
    expect(cp.rx).toBeGreaterThan(0); expect(cp.rx).toBe(cp.ry);
    expect(cp.originX).toBe("center"); expect(cp.originY).toBe("center");
  });
  it("circle → Ellipse, rx==ry(=min/2)", () => {
    const cp: any = buildClipPath("circle", { width: 200, height: 100 }, ctors);
    expect(cp.type).toBe("ellipse");
    expect(cp.rx).toBe(50); expect(cp.ry).toBe(50);
  });
  it("ellipse → Ellipse, rx=w/2, ry=h/2", () => {
    const cp: any = buildClipPath("ellipse", { width: 200, height: 100 }, ctors);
    expect(cp.rx).toBe(100); expect(cp.ry).toBe(50);
  });
  it("maskKindOf: 직렬화 clipPath → kind 추정", () => {
    expect(maskKindOf(null)).toBe("none");
    expect(maskKindOf({ type: "rect", rx: 10 })).toBe("rounded");
    expect(maskKindOf({ type: "ellipse", rx: 50, ry: 50 })).toBe("circle");
    expect(maskKindOf({ type: "ellipse", rx: 100, ry: 50 })).toBe("ellipse");
  });
});
