export type EditorAction = "undo" | "redo" | "duplicate" | "delete" | "save";

/** 키보드 이벤트 → 에디터 액션(없으면 null). 호출부가 preventDefault + 디스패치 담당.
 *  ctrl/meta 동일 취급. 텍스트 인라인 편집 중에는 호출부가 이 함수를 건너뛴다(자연 입력 보존). */
export function keyToEditorAction(e: KeyboardEvent): EditorAction | null {
  const mod = e.ctrlKey || e.metaKey;
  const k = e.key.toLowerCase();
  if (mod && k === "z") return e.shiftKey ? "redo" : "undo";
  if (mod && k === "d") return "duplicate";
  if (mod && k === "s") return "save";
  if (!mod && (e.key === "Delete" || e.key === "Backspace")) return "delete";
  return null;
}
