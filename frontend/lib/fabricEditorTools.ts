/** FabricEditor 순수 로직 — canvas/DOM 비의존(단위 테스트 가능).
 *  필터 값 clamp·저장 페이로드·undo/redo 스택·scene 계약 키를 분리해 검증 가능하게 한다. */

/** scene 계약 보존 — toObject/clone 직렬화 시 반드시 포함할 커스텀 prop 키.
 *  role/lang/slotId가 빠지면 다국어 스왑(swapLanguage)·검토 카피 재구성
 *  (_collect_scene_copy)·composite 렌더가 깨진다. 이 상수가 단일 소스. */
export const SCENE_EXPORT_PROPS = ["role", "lang", "slotId"] as const;

export type FilterValues = { brightness: number; contrast: number; saturation: number };
export const DEFAULT_FILTERS: FilterValues = { brightness: 0, contrast: 0, saturation: 0 };

/** 슬라이더 값을 안전 범위로 clamp(비유한값 → 0). 필터/불투명도 공용. */
export function clampFilter(v: number, min = -1, max = 1): number {
  if (!Number.isFinite(v)) return 0;
  return Math.max(min, Math.min(max, v));
}

/** 저장 페이로드 — canvas.toObject 결과 + 캔버스 치수(aspect 보존).
 *  4:5(1080×1350)가 재오픈 시 정사각으로 되돌아가지 않도록 width/height를 명시 보존. */
export function buildSavePayload(canvasJson: object, width: number, height: number): object {
  return { ...canvasJson, width, height };
}

// --- undo/redo 스택(순수) -------------------------------------------------
export type History = { snapshots: string[]; pointer: number };
const HISTORY_CAP = 30;

export function initHistory(snapshot: string): History {
  return { snapshots: [snapshot], pointer: 0 };
}

/** 현재 포인터 이후(redo 가지)를 버리고 새 스냅샷 push. 상한 초과 시 가장 오래된 것 제거. */
export function pushSnapshot(h: History, snapshot: string, cap = HISTORY_CAP): History {
  if (h.snapshots[h.pointer] === snapshot) return h; // 변화 없음 → no-op
  let snaps = h.snapshots.slice(0, h.pointer + 1);
  snaps.push(snapshot);
  if (snaps.length > cap) snaps = snaps.slice(snaps.length - cap);
  return { snapshots: snaps, pointer: snaps.length - 1 };
}

export function canUndo(h: History): boolean {
  return h.pointer > 0;
}
export function canRedo(h: History): boolean {
  return h.pointer < h.snapshots.length - 1;
}

/** undo → [새 History, 복원할 스냅샷]. 불가하면 스냅샷은 null. */
export function undo(h: History): [History, string | null] {
  if (!canUndo(h)) return [h, null];
  const pointer = h.pointer - 1;
  return [{ ...h, pointer }, h.snapshots[pointer]];
}
export function redo(h: History): [History, string | null] {
  if (!canRedo(h)) return [h, null];
  const pointer = h.pointer + 1;
  return [{ ...h, pointer }, h.snapshots[pointer]];
}
