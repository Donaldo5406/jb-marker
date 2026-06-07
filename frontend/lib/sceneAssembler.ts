export type BBox = { x: number; y: number; w: number; h: number };
export type Slot = {
  role: string;
  // 레퍼런스·실 LLM은 객체({x,y,w,h}), demo_fixtures는 배열([x,y,w,h])을 줄 수 있다.
  bbox: BBox | [number, number, number, number];
  z?: number;
  asset_ref?: string;
  copy_key?: string;
  style_token?: string;
};
export type LayoutSpec = {
  aspect?: string;
  slots: Slot[];
  copy?: Record<string, Record<string, string>>;
};
export type FabricScene = { version: string; objects: any[]; background?: string };

const IMAGE_ROLES = new Set(["background", "logo"]);

/** bbox를 객체({x,y,w,h})·배열([x,y,w,h]) 양식 모두 받아 숫자로 정규화.
 *  배열에 .x로 접근하면 undefined → 모든 슬롯의 left/top/width가 undefined가 되어
 *  텍스트가 원점에 겹치고 이미지 scaleToWidth가 죽는다. 비정상 값은 0 폴백. */
function normBBox(bbox: unknown): BBox {
  const n = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? v : 0);
  if (Array.isArray(bbox)) {
    return { x: n(bbox[0]), y: n(bbox[1]), w: n(bbox[2]), h: n(bbox[3]) };
  }
  const b = (bbox ?? {}) as Partial<BBox>;
  return { x: n(b.x), y: n(b.y), w: n(b.w), h: n(b.h) };
}

/** layout.spec + 언어 → Fabric JSON(toJSON 호환). assetUrl로 asset_ref 해석. */
export function assembleScene(
  spec: LayoutSpec, lang: string, assetUrl: (ref: string) => string,
): FabricScene {
  const copy = spec.copy?.[lang] ?? {};
  const objects = (spec.slots ?? [])
    .slice()
    .sort((a, b) => (a.z ?? 0) - (b.z ?? 0))
    .map((s) => {
      const bb = normBBox(s.bbox);
      const common = {
        left: bb.x, top: bb.y, width: bb.w, height: bb.h,
        role: s.role, slotId: `${s.role}`,
      };
      if (IMAGE_ROLES.has(s.role)) {
        return { ...common, type: "image",
          src: s.asset_ref ? assetUrl(s.asset_ref) : "" };
      }
      const key = s.copy_key ?? s.role;
      return { ...common, type: "textbox", lang,
        text: (key && copy[key]) || "",
        fontSize: 48, fill: "#0b1324" };
    });
  return { version: "6.0.0", objects };
}

/** 텍스트 객체 콘텐츠만 언어 교체(레이아웃·비주얼 보존). */
export function swapLanguage(
  scene: FabricScene, spec: LayoutSpec, lang: string,
): FabricScene {
  const copy = spec.copy?.[lang] ?? {};
  const slotByRole = new Map(spec.slots.map((s) => [s.role, s]));
  return {
    ...scene,
    objects: scene.objects.map((o) => {
      if (o.type !== "textbox") return o;
      const slot = slotByRole.get(o.role);
      const key = slot?.copy_key ?? slot?.role;
      return { ...o, lang, text: (key && copy[key]) || o.text };
    }),
  };
}
