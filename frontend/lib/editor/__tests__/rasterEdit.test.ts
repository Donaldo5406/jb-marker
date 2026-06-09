import { describe, it, expect } from "vitest";
import { editedAssetName, computeRasterSwap } from "../rasterEdit";

describe("editedAssetName", () => {
  it("확장자 분리 후 -edited 접미사 + 새 확장자", () => {
    expect(editedAssetName("poster.jpg", "png")).toBe("poster-edited.png");
  });
  it("점 없는 이름도 처리", () => {
    expect(editedAssetName("image", "png")).toBe("image-edited.png");
  });
  it("빈/누락 이름은 'image' 기본값", () => {
    expect(editedAssetName("", "png")).toBe("image-edited.png");
    expect(editedAssetName(undefined as any, "webp")).toBe("image-edited.webp");
  });
  it("여러 점이 있어도 마지막 확장자만 제거", () => {
    expect(editedAssetName("a.b.c.jpeg", "png")).toBe("a.b.c-edited.png");
  });
});

describe("computeRasterSwap", () => {
  it("표시폭을 보존하도록 균일 스케일 계산(축소)", () => {
    expect(computeRasterSwap(300, 600)).toEqual({ scaleX: 0.5, scaleY: 0.5 });
  });
  it("표시폭 보존(확대)", () => {
    expect(computeRasterSwap(600, 300)).toEqual({ scaleX: 2, scaleY: 2 });
  });
  it("새 자연폭이 0/음수면 스케일 1 폴백(0 나눗셈 방지)", () => {
    expect(computeRasterSwap(300, 0)).toEqual({ scaleX: 1, scaleY: 1 });
    expect(computeRasterSwap(300, -5)).toEqual({ scaleX: 1, scaleY: 1 });
  });
  it("이전 표시폭이 0이어도 1 폴백", () => {
    expect(computeRasterSwap(0, 600)).toEqual({ scaleX: 1, scaleY: 1 });
  });
});
