export type BBox = { x: number; y: number; w: number; h: number };
export type Slot = {
  role: string;
  // 레퍼런스·실 LLM은 객체({x,y,w,h}), demo_fixtures는 배열([x,y,w,h])을 줄 수 있다.
  bbox: BBox | [number, number, number, number];
  z?: number;
  asset_ref?: string;
  copy_key?: string;
  style_token?: string;
  font_px?: number;   // layout.spec의 글자크기(없으면 48 폴백)
  color?: string;     // #RRGGBB 텍스트 색(없으면 #0b1324 폴백)
};
export type LayoutSpec = {
  aspect?: string;
  // 언어별 베이크 배경(풀 포스터) asset_ref 맵. 예: { ko: "...v1.png", en: "...v1.en.png" }.
  visual_by_lang?: Record<string, string>;
  slots: Slot[];
  copy?: Record<string, Record<string, string>>;
};
export type FabricScene = {
  version: string; objects: any[]; background?: string;
  width?: number; height?: number;   // aspect 기반 캔버스 치수(FabricEditor 캔버스 크기)
};

const IMAGE_ROLES = new Set(["background", "logo"]);

const BASE_WIDTH = 1080;

/** aspect("W:H") → 캔버스 치수. 폭 고정(1080), 높이는 비율로 산출. 미지정/이상값은 정사각.
 *  예: "4:5"→{1080,1350}, "1:1"→{1080,1080}, "16:9"→{1080,608}. */
export function aspectToDims(aspect?: string): { width: number; height: number } {
  const m = /^\s*(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)\s*$/.exec(aspect ?? "");
  if (!m) return { width: BASE_WIDTH, height: BASE_WIDTH };
  const w = parseFloat(m[1]);
  const h = parseFloat(m[2]);
  if (!(w > 0) || !(h > 0)) return { width: BASE_WIDTH, height: BASE_WIDTH };
  return { width: BASE_WIDTH, height: Math.round((BASE_WIDTH * h) / w) };
}

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

/** #RRGGBB → 상대 휘도(0~1). 파싱 실패는 어두움(0)으로 간주. */
function relLuminance(hex: string): number {
  const m = /^#?([0-9a-fA-F]{6})$/.exec(hex ?? "");
  if (!m) return 0;
  const n = parseInt(m[1], 16);
  const r = ((n >> 16) & 255) / 255, g = ((n >> 8) & 255) / 255, b = (n & 255) / 255;
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** 텍스트 슬롯 뒤에 깔 반투명 스크림 rect. 밝은 글자→어두운 스크림, 그 반대도. */
function scrimFor(bb: BBox, color: string, role: string): any {
  const fill = relLuminance(color) > 0.5 ? "rgba(0,0,0,0.38)" : "rgba(255,255,255,0.42)";
  const pad = 12;
  return {
    type: "rect", left: bb.x - pad, top: bb.y - pad,
    width: bb.w + pad * 2, height: bb.h + pad * 2,
    fill, rx: 8, ry: 8, role: "scrim", slotId: role,
  };
}

/** 로고 뒤 밝은 라운드 플레이트(대비 보장). 배경이 어두우면 네이비 로고가 묻히므로(실측)
 *  로고 bbox보다 살짝 크게 반투명 화이트 판을 깔아 배경과 무관한 가독성을 확보한다
 *  (실제 은행 포스터의 로고 락업 방식). role="logo_plate"라 scrim 카운트에 영향 없음. */
function logoPlate(bb: BBox): any {
  const pad = 14;
  return {
    type: "rect", left: bb.x - pad, top: bb.y - pad,
    width: bb.w + pad * 2, height: bb.h + pad * 2,
    fill: "rgba(255,255,255,0.92)", rx: 12, ry: 12,
    role: "logo_plate", slotId: "logo",
  };
}

/** layout.spec + 언어 → Fabric JSON(toJSON 호환). assetUrl로 asset_ref 해석. */
export function assembleScene(
  spec: LayoutSpec, lang: string, assetUrl: (ref: string) => string,
): FabricScene {
  const copy = spec.copy?.[lang] ?? {};
  const objects = (spec.slots ?? [])
    .slice()
    .sort((a, b) => (a.z ?? 0) - (b.z ?? 0))
    .flatMap((s) => {
      const bb = normBBox(s.bbox);
      const common = {
        left: bb.x, top: bb.y, width: bb.w, height: bb.h,
        role: s.role, slotId: `${s.role}`,
      };
      if (IMAGE_ROLES.has(s.role)) {
        // 배경(풀 포스터)은 언어별 베이크 visual을 visual_by_lang에서 해석, 없으면 슬롯 asset_ref 폴백.
        const ref = s.role === "background"
          ? (spec.visual_by_lang?.[lang] ?? s.asset_ref)
          : s.asset_ref;
        const img = { ...common, type: "image", src: ref ? assetUrl(ref) : "" };
        // 로고는 대비 보장용 밝은 플레이트를 뒤에 깔고(먼저 방출=낮은 z) 그 위에 로고 이미지.
        if (s.role === "logo") return [logoPlate(bb), img];
        return [img];
      }
      // 헤드라인/바디/CTA는 배경에 베이크됨 → 어떤 객체도 방출하지 않음. disclosure만 오버레이.
      if (s.role !== "disclosure") return [];
      const key = s.copy_key ?? s.role;
      const color = s.color ?? "#0b1324";
      const textbox = { ...common, type: "textbox", lang,
        text: (key && copy[key]) || "",
        fontSize: s.font_px ?? 30, fill: color };
      // 스크림을 먼저(낮은 z), 텍스트를 그 위로
      return [scrimFor(bb, color, s.role), textbox];
    });
  const { width, height } = aspectToDims(spec.aspect);
  return { version: "6.0.0", objects, width, height };
}

/** 원-레이어 언어 교체: 베이크 배경(visual_by_lang) + disclosure 텍스트를 언어별 교체.
 *  로고·레이아웃은 보존. assetUrl로 언어별 배경 asset_ref를 해석. */
export function swapLanguage(
  scene: FabricScene, spec: LayoutSpec, lang: string, assetUrl: (ref: string) => string,
): FabricScene {
  const copy = spec.copy?.[lang] ?? {};
  const slotByRole = new Map(spec.slots.map((s) => [s.role, s]));
  const bgRef = spec.visual_by_lang?.[lang];
  return {
    ...scene,
    objects: scene.objects.map((o) => {
      if (o.role === "background" && bgRef) return { ...o, src: assetUrl(bgRef) };
      if (o.type !== "textbox") return o;
      const slot = slotByRole.get(o.role);
      const key = slot?.copy_key ?? slot?.role;
      return { ...o, lang, text: (key && copy[key]) || o.text };
    }),
  };
}
