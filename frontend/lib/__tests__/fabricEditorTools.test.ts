import { describe, it, expect } from "vitest";
import {
  SCENE_EXPORT_PROPS, clampFilter, buildSavePayload,
  initHistory, pushSnapshot, undo, redo, canUndo, canRedo,
} from "@/lib/fabricEditorTools";

describe("fabricEditorTools", () => {
  it("SCENE_EXPORT_PROPS는 계약 키(role/lang/slotId)를 포함한다", () => {
    // 회귀 가드: 이 키가 빠지면 다국어 스왑·검토 카피 재구성이 깨진다.
    expect(SCENE_EXPORT_PROPS).toContain("role");
    expect(SCENE_EXPORT_PROPS).toContain("lang");
    expect(SCENE_EXPORT_PROPS).toContain("slotId");
  });

  it("clampFilter는 범위로 자르고 비유한값은 0", () => {
    expect(clampFilter(0.5)).toBe(0.5);
    expect(clampFilter(2)).toBe(1);
    expect(clampFilter(-3)).toBe(-1);
    expect(clampFilter(NaN)).toBe(0);
    expect(clampFilter(5, 0, 2)).toBe(2);
  });

  it("buildSavePayload는 canvas json + 캔버스 치수를 보존한다", () => {
    const out: any = buildSavePayload({ version: "6", objects: [{ role: "headline" }] }, 1080, 1350);
    expect(out.width).toBe(1080);
    expect(out.height).toBe(1350);
    expect(out.objects[0].role).toBe("headline");
  });

  it("history: init→push→undo→redo 라운드트립", () => {
    let h = initHistory("A");
    expect(canUndo(h)).toBe(false);
    expect(canRedo(h)).toBe(false);
    h = pushSnapshot(h, "B");
    h = pushSnapshot(h, "C");
    expect(canUndo(h)).toBe(true);

    const [h2, snapU] = undo(h);
    expect(snapU).toBe("B");
    expect(canRedo(h2)).toBe(true);

    const [h3, snapR] = redo(h2);
    expect(snapR).toBe("C");
    expect(canRedo(h3)).toBe(false);
  });

  it("동일 스냅샷 push는 no-op", () => {
    let h = initHistory("A");
    h = pushSnapshot(h, "A");
    expect(h.snapshots.length).toBe(1);
  });

  it("push는 redo 가지를 버린다(분기 후 새 작업)", () => {
    let h = initHistory("A");
    h = pushSnapshot(h, "B");
    const [hu] = undo(h);            // pointer→A
    const h2 = pushSnapshot(hu, "C"); // A 이후 새 분기 → B 폐기
    expect(canRedo(h2)).toBe(false);
    expect(h2.snapshots).toEqual(["A", "C"]);
  });

  it("undo 불가 시 스냅샷 null", () => {
    const [, snap] = undo(initHistory("A"));
    expect(snap).toBeNull();
  });

  it("스택 상한(cap) 초과 시 오래된 것부터 제거", () => {
    let h = initHistory("0");
    for (let i = 1; i <= 5; i++) h = pushSnapshot(h, String(i), 3);
    expect(h.snapshots.length).toBe(3);
    expect(h.snapshots).toEqual(["3", "4", "5"]);
  });
});
