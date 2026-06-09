// frontend/lib/editor/imageFilters.ts
/** 이미지 비파괴 보정 파라미터(평면값)와 Fabric 네이티브 필터 인스턴스 간 변환 순수 헬퍼.
 *  값 범위는 Fabric을 그대로 따른다(brightness/contrast/saturation −1..1, blur 0..1). */

export type FilterParams = {
  brightness: number;   // −1..1, 0=원본
  contrast: number;     // −1..1, 0=원본
  saturation: number;   // −1..1, 0=원본
  blur: number;         // 0..1, 0=없음
  grayscale: boolean;   // true=흑백
};

export const FILTER_DEFAULTS: FilterParams = {
  brightness: 0, contrast: 0, saturation: 0, blur: 0, grayscale: false,
};

/** Fabric filters 네임스페이스 생성자 모음(DesignEditor가 주입; 테스트는 스텁). */
export type FilterCtors = {
  Brightness: new (o: { brightness: number }) => any;
  Contrast: new (o: { contrast: number }) => any;
  Saturation: new (o: { saturation: number }) => any;
  Blur: new (o: { blur: number }) => any;
  Grayscale: new () => any;
};

/** FilterParams → Fabric 필터 인스턴스 배열. 중립(기본값)은 제외해 .scene 직렬화를 가볍게 유지. */
export function buildFabricFilters(params: FilterParams, ctors: FilterCtors): any[] {
  const out: any[] = [];
  if (params.brightness !== 0) out.push(new ctors.Brightness({ brightness: params.brightness }));
  if (params.contrast !== 0) out.push(new ctors.Contrast({ contrast: params.contrast }));
  if (params.saturation !== 0) out.push(new ctors.Saturation({ saturation: params.saturation }));
  if (params.blur !== 0) out.push(new ctors.Blur({ blur: params.blur }));
  if (params.grayscale) out.push(new ctors.Grayscale());
  return out;
}

/** Fabric 필터 인스턴스/직렬화 객체 배열 → FilterParams. type(대소문자 무시)으로 값 추출.
 *  로드된 씬(toObject)·라이브 img.filters 양쪽 모두 동작. */
export function extractFilterParams(filtersArray: any[] | undefined | null): FilterParams {
  const p: FilterParams = { ...FILTER_DEFAULTS };
  for (const f of filtersArray ?? []) {
    if (!f) continue;
    const t = String(f.type ?? "").toLowerCase();
    if (t === "brightness") p.brightness = Number(f.brightness ?? 0);
    else if (t === "contrast") p.contrast = Number(f.contrast ?? 0);
    else if (t === "saturation") p.saturation = Number(f.saturation ?? 0);
    else if (t === "blur") p.blur = Number(f.blur ?? 0);
    else if (t === "grayscale") p.grayscale = true;
  }
  return p;
}
