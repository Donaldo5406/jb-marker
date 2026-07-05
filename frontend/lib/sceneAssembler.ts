import { DEFAULT_FONT } from "./design/fontStack";
import { iconSrc } from "./editor/iconRegistry";

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
  // vector_chrome 확장
  font_family?: string;
  weight?: number;
  align?: "left" | "center" | "right";
  scrim?: boolean;
  container?: { fill?: string; radius?: number; opacity?: number; shadow?: boolean };
  lines?: { text: string; style: "label" | "figure" | "caption" }[];
  items?: { icon_key: string; title: string; desc: string }[];
  fill?: string;
  text_color?: string;
  radius?: number;
};
export type LayoutSpec = {
  aspect?: string;
  // 언어별 베이크 배경(풀 포스터) asset_ref 맵. 예: { ko: "...v1.png", en: "...v1.en.png" }.
  visual_by_lang?: Record<string, string>;
  render_mode?: "baked" | "vector_chrome";
  // "baked"면 로고·고지·CTA가 포스터에 이미 구워짐(poc_E 자산) → 결정론 오버레이를
  // 얹지 않는다(이중 오버레이 방지). 로고는 slots에서 제외되고, 고지는 아래 assembleScene이
  // 오버레이 렌더를 건너뛴다.
  logo_policy?: "baked" | string;
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

/** layout.spec + 언어 → Fabric JSON(toJSON 호환). assetUrl로 asset_ref 해석.
 *  로고는 별도 플레이트 없이 베이크가 남긴 밝은 세이프존 코너 위에 정확한 오버레이로 얹는다
 *  (플레이트는 얹힌 카드처럼 정합성이 떨어져 제거 — 베이크가 코너 배경을 담당, 오버레이가 정확 로고). */
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
        return [{ ...common, type: "image", src: ref ? assetUrl(ref) : "" }];
      }
      // 헤드라인/바디/CTA는 baked 모드에서 배경에 구워짐 → 미방출. disclosure만 오버레이.
      if (s.role === "disclosure") {
        // logo_policy="baked"(poc_E): 고지도 로고·CTA와 함께 포스터에 이미 구워져 있어
        // 오버레이 텍스트+스크림을 얹으면 이중이 된다 → disclosure 오버레이 건너뜀.
        // (레이아웃 spec의 disclosure 슬롯은 유지 — 시각 적법성 룰이 존재·비율을 읽는다.)
        if (spec.logo_policy === "baked") return [];
        const key = s.copy_key ?? s.role;
        const color = s.color ?? "#0b1324";
        const textbox: any = { ...common, type: "textbox", lang,
          text: (key && copy[key]) || "",
          fontSize: s.font_px ?? 30, fill: color };
        // vector_chrome 모드에서만 서체 통일(baked는 현행 바이트 동등 유지 — spec §8 안전).
        if ((spec.render_mode ?? "baked") === "vector_chrome") {
          textbox.fontFamily = s.font_family ?? DEFAULT_FONT;
        }
        return [scrimFor(bb, color, s.role), textbox];
      }
      if ((spec.render_mode ?? "baked") !== "vector_chrome") return [];  // baked: 텍스트 미방출(하위호환)
      // vector_chrome: 텍스트/위젯 role을 편집 벡터로 방출
      const emitted = renderVectorRole(s, bb, common, lang, copy);
      return s.scrim ? [scrimFor(bb, s.color ?? "#0b1324", s.role), ...emitted] : emitted;
    });
  const { width, height } = aspectToDims(spec.aspect);
  return { version: "6.0.0", objects, width, height };
}

/** vector_chrome 모드: role별 편집 Fabric 객체 방출. Task2~5에서 rate_card/benefit_row/cta_button 확장. */
function renderVectorRole(
  s: Slot, bb: BBox, common: Record<string, any>, lang: string,
  copy: Record<string, string>,
): any[] {
  const RATE_STYLE: Record<string, { size: number; weight: number }> = {
    figure: { size: 72, weight: 800 }, label: { size: 28, weight: 600 }, caption: { size: 24, weight: 400 },
  };
  if (s.role === "rate_card" && Array.isArray(s.lines)) {
    const c = s.container ?? {};
    const rect = {
      ...common, type: "rect", fill: c.fill ?? "#FFFFFF",
      rx: c.radius ?? 16, ry: c.radius ?? 16, opacity: c.opacity ?? 0.94,
      shadow: c.shadow ? "rgba(0,0,0,0.18) 0px 8px 24px" : null,
    };
    const pad = 24;
    let y = bb.y + pad;
    const lines = s.lines.map((ln) => {
      const st = RATE_STYLE[ln.style] ?? RATE_STYLE.caption;
      const t = { type: "textbox", role: "rate_card", slotId: "rate_card", lang,
        left: bb.x + pad, top: y, width: bb.w - pad * 2,
        text: ln.text, fontSize: st.size, fontWeight: st.weight,
        fontFamily: s.font_family ?? DEFAULT_FONT, fill: s.color ?? "#0B1324", textAlign: "left" };
      y += st.size + 10;
      return t;
    });
    return [rect, ...lines];
  }
  if (s.role === "benefit_row" && Array.isArray(s.items)) {
    const n = Math.max(1, s.items.length);
    const colW = bb.w / n;
    const iconSize = 44;
    const out: any[] = [];
    s.items.forEach((it, i) => {
      const cx = bb.x + colW * i;                 // 칼럼 좌측
      const iconLeft = cx + (colW - iconSize) / 2; // 칼럼 내 중앙
      out.push({ type: "image", role: "benefit_row", slotId: "benefit_row",
        left: iconLeft, top: bb.y, width: iconSize, height: iconSize,
        src: iconSrc(it.icon_key) });
      out.push({ type: "textbox", role: "benefit_row", slotId: "benefit_row", lang,
        left: cx, top: bb.y + iconSize + 8, width: colW,
        text: it.title, fontSize: 26, fontWeight: 700,
        fontFamily: s.font_family ?? DEFAULT_FONT, fill: s.color ?? "#0B1324", textAlign: "center" });
      out.push({ type: "textbox", role: "benefit_row", slotId: "benefit_row", lang,
        left: cx, top: bb.y + iconSize + 40, width: colW,
        text: it.desc, fontSize: 22, fontWeight: 400,
        fontFamily: s.font_family ?? DEFAULT_FONT, fill: s.color ?? "#3A3A3A", textAlign: "center" });
    });
    return out;
  }
  if (s.role === "cta_button") {
    const rect = { ...common, type: "rect", fill: s.fill ?? "#0066FF",
      rx: s.radius ?? 999, ry: s.radius ?? 999 };
    const key = s.copy_key ?? "cta";
    const txt = { type: "textbox", role: "cta_button", slotId: "cta_button", lang,
      left: bb.x, top: bb.y + Math.max(0, (bb.h - (s.font_px ?? 40)) / 2), width: bb.w,
      text: (key && copy[key]) || "", fontSize: s.font_px ?? 40, fontWeight: s.weight ?? 700,
      fontFamily: s.font_family ?? DEFAULT_FONT, fill: s.text_color ?? "#FFFFFF", textAlign: "center" };
    return [rect, txt];
  }
  const key = s.copy_key ?? s.role;
  const textbox = {
    ...common, type: "textbox", lang,
    text: (key && copy[key]) || "",
    fontSize: s.font_px ?? 40,
    fontFamily: s.font_family ?? DEFAULT_FONT,
    fontWeight: s.weight ?? 400,
    textAlign: s.align ?? "left",
    fill: s.color ?? "#0b1324",
  };
  return [textbox];
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
