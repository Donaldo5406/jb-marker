export type Box = { left: number; top: number; width: number; height: number };
export type AlignMode = "left" | "hcenter" | "right" | "top" | "vcenter" | "bottom";
export type Patch = { left?: number; top?: number };

/** boxes의 합집합 경계(좌상단~우하단). */
function union(boxes: Box[]): Box {
  const minL = Math.min(...boxes.map((b) => b.left));
  const minT = Math.min(...boxes.map((b) => b.top));
  const maxR = Math.max(...boxes.map((b) => b.left + b.width));
  const maxB = Math.max(...boxes.map((b) => b.top + b.height));
  return { left: minL, top: minT, width: maxR - minL, height: maxB - minT };
}

/** 정렬. 1개면 bounds(캔버스) 기준, 2개+면 선택 묶음 합집합 기준. 변경 축만 패치로 반환. */
export function alignBoxes(boxes: Box[], mode: AlignMode, bounds: Box): Patch[] {
  if (boxes.length === 0) return [];
  const ref = boxes.length > 1 ? union(boxes) : bounds;
  return boxes.map((b) => {
    switch (mode) {
      case "left": return { left: ref.left };
      case "right": return { left: ref.left + ref.width - b.width };
      case "hcenter": return { left: ref.left + ref.width / 2 - b.width / 2 };
      case "top": return { top: ref.top };
      case "bottom": return { top: ref.top + ref.height - b.height };
      case "vcenter": return { top: ref.top + ref.height / 2 - b.height / 2 };
    }
  });
}

/** 균등 분배. 정렬 축(left/top) 기준 양끝 고정, 사이를 등간격 재배치. 3개 미만은 no-op. */
export function distributeBoxes(boxes: Box[], axis: "h" | "v"): Patch[] {
  const key = axis === "h" ? "left" : "top";
  if (boxes.length < 3) return boxes.map(() => ({}));
  const order = boxes.map((b, i) => ({ i, v: b[key] })).sort((a, b) => a.v - b.v);
  const first = order[0].v;
  const last = order[order.length - 1].v;
  const step = (last - first) / (order.length - 1);
  const out: Patch[] = boxes.map(() => ({}));
  order.forEach((o, rank) => { out[o.i] = { [key]: first + step * rank }; });
  return out;
}

/** value를 threshold 이내 가장 가까운 target으로 스냅. 없으면 null. */
export function snapValue(value: number, targets: number[], threshold: number): number | null {
  let best: number | null = null;
  let bestD = threshold;
  for (const t of targets) {
    const d = Math.abs(value - t);
    if (d <= bestD) { bestD = d; best = t; }
  }
  return best;
}
