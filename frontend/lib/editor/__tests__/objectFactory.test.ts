import { describe, it, expect } from "vitest";
import { buildObjectSpec } from "../objectFactory";

describe("buildObjectSpec", () => {
  const C = { x: 540, y: 540 };
  it("rect: 중앙 정렬된 사각형 스펙", () => {
    const s = buildObjectSpec("rect", C);
    expect(s.ctor).toBe("rect");
    expect(s.props).toMatchObject({ left: 440, top: 480, width: 200, height: 120 });
    expect(typeof s.props.fill).toBe("string");
  });
  it("circle: radius 60, 중앙 정렬", () => {
    const s = buildObjectSpec("circle", C);
    expect(s.ctor).toBe("circle");
    expect(s.props).toMatchObject({ left: 480, top: 480, radius: 60 });
  });
  it("textbox: 기본 텍스트 + 폭 300, 중앙 정렬", () => {
    const s = buildObjectSpec("textbox", C);
    expect(s.ctor).toBe("textbox");
    expect(s.props.width).toBe(300);
    expect(s.props.left).toBe(390);
    expect(typeof s.props.text).toBe("string");
    expect(s.props.text.length).toBeGreaterThan(0);
  });
  it("line: 가로 200px, 중앙 통과 points", () => {
    const s = buildObjectSpec("line", C);
    expect(s.ctor).toBe("line");
    expect(s.props.points).toEqual([440, 540, 640, 540]);
    expect(s.props.strokeWidth).toBeGreaterThan(0);
  });
});
