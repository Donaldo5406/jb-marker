// frontend/lib/editor/imageCrop.ts
/** 비파괴 종횡비 크롭 순수 헬퍼. 원본(자연) 치수에서 중앙 정렬된 최대 부분 사각형을 계산.
 *  Fabric 이미지에 {cropX, cropY, width, height}로 적용하면 소스 픽셀은 보존, 표시 영역만 바뀐다. */

export type AspectKey = "free" | "1:1" | "4:5" | "16:9";
export type CropRect = { cropX: number; cropY: number; width: number; height: number };

const RATIOS: Record<Exclude<AspectKey, "free">, number> = { "1:1": 1, "4:5": 4 / 5, "16:9": 16 / 9 };

/** 원본 치수 + 종횡비 → 중앙 크롭 사각형. "free"=크롭 해제(전체 복원). */
export function computeAspectCrop(natW: number, natH: number, aspect: AspectKey): CropRect {
  if (aspect === "free") return { cropX: 0, cropY: 0, width: natW, height: natH };
  const target = RATIOS[aspect];
  const imgRatio = natW / natH;
  let width: number, height: number;
  if (imgRatio > target) { height = natH; width = natH * target; }
  else { width = natW; height = natW / target; }
  return { cropX: (natW - width) / 2, cropY: (natH - height) / 2, width, height };
}
