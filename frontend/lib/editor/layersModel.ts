import type { SceneObject } from "./sceneSerialize";

export type LayerRow = {
  index: number;        // 캔버스 객체 인덱스(0=맨 뒤)
  type: string;
  role?: string;
  label: string;
  visible: boolean;
  locked: boolean;      // Fabric evented=false & selectable=false 를 잠금으로 간주
};

/** 캔버스 객체 배열 → 레이어 행. 목록은 시각적 위→아래(캔버스 인덱스 역순). */
export function toLayers(objects: SceneObject[]): LayerRow[] {
  return objects
    .map((o, index) => {
      const type = String(o.type ?? "object");
      const text = typeof o.text === "string" ? o.text.trim() : "";
      const label = type === "textbox" && text ? text.slice(0, 18) : (o.role ?? type);
      return {
        index, type, role: o.role,
        label: String(label),
        visible: o.visible !== false,
        locked: o.evented === false,
      };
    })
    .reverse();
}
