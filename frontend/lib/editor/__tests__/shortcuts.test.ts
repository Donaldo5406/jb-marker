import { describe, it, expect } from "vitest";
import { keyToEditorAction } from "../shortcuts";

const ev = (o: Partial<KeyboardEvent>): KeyboardEvent => o as KeyboardEvent;

describe("keyToEditorAction", () => {
  it("Ctrl+Z → undo, Ctrl+Shift+Z → redo", () => {
    expect(keyToEditorAction(ev({ key: "z", ctrlKey: true }))).toBe("undo");
    expect(keyToEditorAction(ev({ key: "z", ctrlKey: true, shiftKey: true }))).toBe("redo");
  });
  it("Meta(⌘) 도 Ctrl처럼 동작", () => {
    expect(keyToEditorAction(ev({ key: "z", metaKey: true }))).toBe("undo");
  });
  it("Ctrl+D → duplicate, Delete/Backspace → delete", () => {
    expect(keyToEditorAction(ev({ key: "d", ctrlKey: true }))).toBe("duplicate");
    expect(keyToEditorAction(ev({ key: "Delete" }))).toBe("delete");
    expect(keyToEditorAction(ev({ key: "Backspace" }))).toBe("delete");
  });
  it("Ctrl+S → save", () => {
    expect(keyToEditorAction(ev({ key: "s", ctrlKey: true }))).toBe("save");
  });
  it("매핑 없는 키 → null", () => {
    expect(keyToEditorAction(ev({ key: "q" }))).toBeNull();
    expect(keyToEditorAction(ev({ key: "a", ctrlKey: true }))).toBeNull();
  });
});
