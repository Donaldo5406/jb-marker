import { describe, it, expect } from "vitest";
import { buildFabricFilters, extractFilterParams, FILTER_DEFAULTS, type FilterParams } from "../imageFilters";

// Fabric 필터 생성자 스텁: 인스턴스가 toObject 직렬화 형상({type, value})을 모사.
const ctors = {
  Brightness: class { type = "Brightness"; brightness: number; constructor(o: any) { this.brightness = o.brightness; } },
  Contrast: class { type = "Contrast"; contrast: number; constructor(o: any) { this.contrast = o.contrast; } },
  Saturation: class { type = "Saturation"; saturation: number; constructor(o: any) { this.saturation = o.saturation; } },
  Blur: class { type = "Blur"; blur: number; constructor(o: any) { this.blur = o.blur; } },
  Grayscale: class { type = "Grayscale"; },
} as any;

describe("imageFilters", () => {
  it("FILTER_DEFAULTS는 전부 중립", () => {
    expect(FILTER_DEFAULTS).toEqual({ brightness: 0, contrast: 0, saturation: 0, blur: 0, grayscale: false });
  });
  it("buildFabricFilters: 중립값은 제외, 설정된 것만 인스턴스화", () => {
    const params: FilterParams = { brightness: 0.3, contrast: 0, saturation: -0.2, blur: 0, grayscale: true };
    const out = buildFabricFilters(params, ctors);
    const types = out.map((f) => f.type).sort();
    expect(types).toEqual(["Brightness", "Grayscale", "Saturation"]);
    expect(out.find((f) => f.type === "Brightness").brightness).toBe(0.3);
    expect(out.find((f) => f.type === "Saturation").saturation).toBe(-0.2);
  });
  it("buildFabricFilters: 전부 중립이면 빈 배열", () => {
    expect(buildFabricFilters(FILTER_DEFAULTS, ctors)).toEqual([]);
  });
  it("extractFilterParams: 직렬화 배열 → params 라운드트립(type 대소문자 무시)", () => {
    const arr = [{ type: "Brightness", brightness: 0.5 }, { type: "blur", blur: 0.4 }, { type: "Grayscale" }];
    expect(extractFilterParams(arr)).toEqual({ brightness: 0.5, contrast: 0, saturation: 0, blur: 0.4, grayscale: true });
  });
  it("extractFilterParams: null/undefined → defaults", () => {
    expect(extractFilterParams(undefined)).toEqual(FILTER_DEFAULTS);
    expect(extractFilterParams(null)).toEqual(FILTER_DEFAULTS);
  });
  it("build→extract 왕복 일관성", () => {
    const params: FilterParams = { brightness: 0.1, contrast: 0.2, saturation: 0.3, blur: 0.5, grayscale: false };
    expect(extractFilterParams(buildFabricFilters(params, ctors))).toEqual(params);
  });
});
