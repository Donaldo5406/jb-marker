// frontend/lib/editor/clipMask.ts
/** 이미지 마스크(clipPath) 순수 헬퍼. 이미지의 (크롭된) 표시 치수에 맞춘 도형 clipPath를 만든다.
 *  Fabric은 clipPath를 객체 중심 기준(originX/Y="center", left/top=0, absolutePositioned=false)으로 클립한다. */

export type MaskKind = "none" | "rounded" | "circle" | "ellipse";
export type MaskDims = { width: number; height: number };

/** 마스크 생성자(DesignEditor가 fabric Rect/Ellipse 주입). */
export type MaskCtors = {
  Rect: new (o: Record<string, unknown>) => any;
  Ellipse: new (o: Record<string, unknown>) => any;
};

/** MaskKind → clipPath 인스턴스(none이면 null). dims=이미지 표시 치수. */
export function buildClipPath(kind: MaskKind, dims: MaskDims, ctors: MaskCtors): any | null {
  const { width, height } = dims;
  const base = { originX: "center", originY: "center", left: 0, top: 0 };
  if (kind === "rounded") {
    const r = Math.min(width, height) * 0.12;
    return new ctors.Rect({ ...base, width, height, rx: r, ry: r });
  }
  if (kind === "circle") {
    const d = Math.min(width, height);
    return new ctors.Ellipse({ ...base, rx: d / 2, ry: d / 2 });
  }
  if (kind === "ellipse") {
    return new ctors.Ellipse({ ...base, rx: width / 2, ry: height / 2 });
  }
  return null;
}

/** 로드/직렬화된 clipPath → 현재 MaskKind 추정(UI 초기값). */
export function maskKindOf(clipPath: any | undefined | null): MaskKind {
  if (!clipPath) return "none";
  const t = String(clipPath.type ?? "").toLowerCase();
  if (t === "rect") return "rounded";
  if (t === "ellipse") return Math.abs((clipPath.rx ?? 0) - (clipPath.ry ?? 0)) < 0.5 ? "circle" : "ellipse";
  return "none";
}
