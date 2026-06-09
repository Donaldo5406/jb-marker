import { describe, it, expect } from "vitest";
import { alignBoxes, distributeBoxes, snapValue, type Box } from "../align";

const bounds: Box = { left: 0, top: 0, width: 1080, height: 1080 };

describe("alignBoxes", () => {
  it("단일 객체: bounds(캔버스) 기준 정렬", () => {
    const b: Box[] = [{ left: 10, top: 10, width: 100, height: 50 }];
    expect(alignBoxes(b, "left", bounds)).toEqual([{ left: 0 }]);
    expect(alignBoxes(b, "right", bounds)).toEqual([{ left: 980 }]);
    expect(alignBoxes(b, "hcenter", bounds)).toEqual([{ left: 490 }]);
    expect(alignBoxes(b, "top", bounds)).toEqual([{ top: 0 }]);
    expect(alignBoxes(b, "bottom", bounds)).toEqual([{ top: 1030 }]);
    expect(alignBoxes(b, "vcenter", bounds)).toEqual([{ top: 515 }]);
  });
  it("다중 객체: 선택 묶음 합집합 기준 정렬", () => {
    const b: Box[] = [
      { left: 0, top: 0, width: 100, height: 100 },
      { left: 200, top: 50, width: 100, height: 100 },
    ];
    expect(alignBoxes(b, "left", bounds)).toEqual([{ left: 0 }, { left: 0 }]);
    expect(alignBoxes(b, "right", bounds)).toEqual([{ left: 200 }, { left: 200 }]);
  });
});

describe("distributeBoxes", () => {
  it("가로 균등 분배: 양끝 고정, 중간 재배치", () => {
    const b: Box[] = [
      { left: 0, top: 0, width: 20, height: 20 },
      { left: 50, top: 0, width: 20, height: 20 },
      { left: 200, top: 0, width: 20, height: 20 },
    ];
    expect(distributeBoxes(b, "h")).toEqual([{ left: 0 }, { left: 100 }, { left: 200 }]);
  });
  it("3개 미만이면 no-op(빈 패치)", () => {
    const b: Box[] = [{ left: 0, top: 0, width: 20, height: 20 }, { left: 50, top: 0, width: 20, height: 20 }];
    expect(distributeBoxes(b, "h")).toEqual([{}, {}]);
  });
});

describe("snapValue", () => {
  it("threshold 이내 가장 가까운 target으로 스냅", () => {
    expect(snapValue(7, [0, 100, 1080], 8)).toBe(0);
    expect(snapValue(96, [0, 100], 8)).toBe(100);
  });
  it("threshold 밖이면 null", () => {
    expect(snapValue(50, [0, 100], 8)).toBeNull();
  });
});
