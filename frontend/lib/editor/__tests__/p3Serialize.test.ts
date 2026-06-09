import { describe, it, expect } from "vitest";
import { SCENE_CUSTOM_PROPS } from "../sceneSerialize";
import { buildFabricFilters, extractFilterParams, type FilterParams } from "../imageFilters";

// 실제 Fabric 필터 직렬화 형상({type, value})을 모사하는 스텁(toObject 결과 모방).
const ctors = {
  Brightness: class { type = "Brightness"; brightness: number; constructor(o: any) { this.brightness = o.brightness; }
    toObject() { return { type: "Brightness", brightness: this.brightness }; } },
  Contrast: class { type = "Contrast"; contrast: number; constructor(o: any) { this.contrast = o.contrast; }
    toObject() { return { type: "Contrast", contrast: this.contrast }; } },
  Saturation: class { type = "Saturation"; saturation: number; constructor(o: any) { this.saturation = o.saturation; }
    toObject() { return { type: "Saturation", saturation: this.saturation }; } },
  Blur: class { type = "Blur"; blur: number; constructor(o: any) { this.blur = o.blur; }
    toObject() { return { type: "Blur", blur: this.blur }; } },
  Grayscale: class { type = "Grayscale"; toObject() { return { type: "Grayscale" }; } },
} as any;

describe("P3 직렬화 회귀", () => {
  it("SCENE_CUSTOM_PROPS는 filters를 포함(P3 보정 보존 계약)", () => {
    expect(SCENE_CUSTOM_PROPS).toContain("filters");
  });
  it("필터 인스턴스 toObject() → extractFilterParams 왕복", () => {
    const params: FilterParams = { brightness: 0.3, contrast: -0.1, saturation: 0, blur: 0.2, grayscale: true };
    const serialized = buildFabricFilters(params, ctors).map((f) => f.toObject()); // .scene에 저장될 형상
    expect(extractFilterParams(serialized)).toEqual(params);
  });
});
