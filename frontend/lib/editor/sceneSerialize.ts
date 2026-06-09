/** Fabric canvas.toObject(propertiesToInclude)에 넘길 커스텀 prop 목록.
 *  role/lang/slotId는 ReviewStudio(법률·다국어)·DeployStudio가 텍스트 레이어를 식별하는 키 —
 *  직렬화에서 누락되면 저장 라운드트립에 구조가 소실된다. filters는 P3 비파괴 보정 보존용(P1부터 포함). */
export const SCENE_CUSTOM_PROPS = ["role", "lang", "slotId", "filters", "assetPath"] as const;

export type SceneObject = Record<string, any> & {
  type?: string; role?: string; lang?: string; slotId?: string;
};
export type ParsedScene = { version?: string; objects: SceneObject[]; width?: number; height?: number };

/** .scene 문자열 → ParsedScene. 비거나 깨지면 null, objects 누락은 []로 정규화. */
export function parseScene(content: string): ParsedScene | null {
  if (!content) return null;
  try {
    const o = JSON.parse(content) as Partial<ParsedScene>;
    return { version: o.version, objects: Array.isArray(o.objects) ? o.objects : [], width: o.width, height: o.height };
  } catch {
    return null;
  }
}
