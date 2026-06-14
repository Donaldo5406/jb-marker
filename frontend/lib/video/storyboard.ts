/** storyboard.spec.json 타입 + 순수 헬퍼. VideoEditor 프리뷰·타임라인·고지 게이트가 소비.
 *  bbox·font_px는 1080×1920(9:16) 참조 좌표계로 가정. */

export type VideoBBox = { x: number; y: number; w: number; h: number };

export type VideoLayer = {
  role: string;          // "headline" | "body" | "cta" | "disclosure"
  copy_key?: string;     // 없으면 role을 키로 사용
  in: number;            // 절대 초
  out: number;
  anim?: string;
  font_px?: number;
  color?: string;
  bbox?: VideoBBox;
};

export type VideoShot = {
  id: string;
  start: number;
  end: number;
  footage_prompt?: string;
  camera?: string;
  transition_in?: string;
  transition_out?: string;
  layers?: VideoLayer[];
};

export type Storyboard = {
  fps?: number;
  bg_color?: string;
  duration_sec?: number;
  aspect?: string;
  shots?: VideoShot[];
  copy?: Record<string, Record<string, string>>; // copy[lang][key]
};

/** 9:16 참조 캔버스(프리뷰 좌표 정규화 기준). */
export const CANVAS_W = 1080;
export const CANVAS_H = 1920;

/** 고지 최소 누적 노출(초). 서버 DISCLOSURE_MIN_SEC와 정합. */
export const DISCLOSURE_MIN_SEC = 3.0;

export function parseStoryboard(content: string): Storyboard | null {
  try {
    const o = JSON.parse(content);
    if (o && typeof o === "object" && !Array.isArray(o)) return o as Storyboard;
  } catch {
    /* 깨진 JSON */
  }
  return null;
}

export function storyboardDuration(sb: Storyboard): number {
  if (typeof sb.duration_sec === "number" && sb.duration_sec > 0) return sb.duration_sec;
  let max = 0;
  for (const s of sb.shots ?? []) max = Math.max(max, s.end ?? 0);
  return max;
}

/** disclosure role 레이어의 누적 노출(초). 단순 합산(겹침 포함, MVP). */
export function disclosureExposure(sb: Storyboard): number {
  let total = 0;
  for (const shot of sb.shots ?? []) {
    for (const l of shot.layers ?? []) {
      if (l.role === "disclosure") total += Math.max(0, (l.out ?? 0) - (l.in ?? 0));
    }
  }
  return Math.round(total * 100) / 100;
}

/** time(초)에 해당하는 샷. 구간 밖이면 첫 샷 폴백(null 방지). */
export function shotAt(sb: Storyboard, t: number): VideoShot | null {
  const shots = sb.shots ?? [];
  for (const s of shots) if (t >= (s.start ?? 0) && t < (s.end ?? 0)) return s;
  return shots[0] ?? null;
}

/** time(초)에 켜져 있는(모든 샷의) 레이어 목록. [in,out) 반열림 구간. */
export function activeLayers(sb: Storyboard, t: number): VideoLayer[] {
  const out: VideoLayer[] = [];
  for (const shot of sb.shots ?? []) {
    for (const l of shot.layers ?? []) {
      if (t >= (l.in ?? 0) && t < (l.out ?? 0)) out.push(l);
    }
  }
  return out;
}

/** 레이어의 표시 텍스트(copy[lang][copy_key||role]). */
export function layerText(sb: Storyboard, layer: VideoLayer, lang: string): string {
  const key = layer.copy_key || layer.role;
  return sb.copy?.[lang]?.[key] ?? "";
}
