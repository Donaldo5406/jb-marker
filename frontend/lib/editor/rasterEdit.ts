/** 리터칭 결과 파일명: 원본 이름의 확장자를 떼고 "-edited" + 새 확장자.
 *  빈/누락 이름은 "image"로 폴백. seq는 assetRestPath가 별도로 prefix하므로 여기선 미관여. */
export function editedAssetName(originalName: string, extension: string): string {
  const base = (originalName || "image").replace(/\.[^.]+$/, "") || "image";
  return `${base}-edited.${extension}`;
}

/** 새 이미지(리터칭본)의 자연폭(newNaturalWidth)에 대해, 캔버스 표시폭(prevScaledWidth)을
 *  보존하도록 균일 스케일을 계산한다. setSrc가 width를 새 자연치수로 리셋하므로 scale 재계산 필요.
 *  잘못된 입력(0/음수)은 1배 폴백(0 나눗셈·역전 방지). 높이는 새 이미지 종횡비를 따른다. */
export function computeRasterSwap(
  prevScaledWidth: number, newNaturalWidth: number,
): { scaleX: number; scaleY: number } {
  if (!(prevScaledWidth > 0) || !(newNaturalWidth > 0)) return { scaleX: 1, scaleY: 1 };
  const s = prevScaledWidth / newNaturalWidth;
  return { scaleX: s, scaleY: s };
}
