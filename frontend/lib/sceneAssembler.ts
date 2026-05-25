export type Slot = {
  role: string;
  bbox: { x: number; y: number; w: number; h: number };
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

/** layout.spec + 언어 → Fabric JSON(toJSON 호환). assetUrl로 asset_ref 해석. */
export function assembleScene(
  spec: LayoutSpec, lang: string, assetUrl: (ref: string) => string,
): FabricScene {
  const copy = spec.copy?.[lang] ?? {};
  const objects = (spec.slots ?? [])
    .slice()
    .sort((a, b) => (a.z ?? 0) - (b.z ?? 0))
    .map((s) => {
      const common = {
        left: s.bbox.x, top: s.bbox.y, width: s.bbox.w, height: s.bbox.h,
        role: s.role, slotId: `${s.role}`,
      };
      if (IMAGE_ROLES.has(s.role)) {
        return { ...common, type: "image",
          src: s.asset_ref ? assetUrl(s.asset_ref) : "" };
      }
      return { ...common, type: "textbox", lang,
        text: (s.copy_key && copy[s.copy_key]) || "",
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
      const key = slot?.copy_key;
      return { ...o, lang, text: (key && copy[key]) || o.text };
    }),
  };
}
